package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strconv"

	"path/filepath"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/shopspring/decimal"

	"github.com/grishinsana/goftx"
	"github.com/grishinsana/goftx/models"
	"github.com/jonhilgart22/go-trader/app/awsUtils"
	"github.com/jonhilgart22/go-trader/app/ftx"
	"github.com/jonhilgart22/go-trader/app/structs"
	"github.com/jonhilgart22/go-trader/app/utils"
)

func DownloadUpdateReuploadData(csvFilename string, inputRecords []*models.HistoricalPrice, constantsMap map[string]string, runningOnAws bool, s3Client *session.Session) (decimal.Decimal, int) {

	// download the files from s3
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], csvFilename, runningOnAws, s3Client)
	// read the data into memory
	records := utils.ReadCsvFile(csvFilename, runningOnAws)
	newestDate, newestCosePrice := utils.FindNewestData(records)
	log.Println(newestCosePrice, "newestCosePrice")
	log.Println(newestDate, "newestDate")
	// add new data as needed
	numRecordsWritten := utils.WriteNewCsvData(inputRecords, newestDate, csvFilename, runningOnAws)
	log.Println(numRecordsWritten, "numRecordsWritten inside of DownloadUpdateReuploadData")

	awsUtils.UploadToS3(constantsMap["s3_bucket"], csvFilename, runningOnAws, s3Client)

	return newestCosePrice, numRecordsWritten

}

func runPythonMlProgram(constantsMap map[string]string, coinToPredict string) {
	pwd, err := os.Getwd()
	if err != nil {
		log.Println(err)
		os.Exit(1)
	}
	log.Println("Current working directory = ", pwd)

	cmd := exec.Command("python3", filepath.Join(pwd, constantsMap["python_script_path"]), fmt.Sprintf("--coin_to_predict=%v", coinToPredict))
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		panic(err)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		os.Exit(1)
		panic(err)

	}
	err = cmd.Start()
	if err != nil {
		os.Exit(1)
		panic(err)
	}

	go utils.CopyOutput(stdout)
	go utils.CopyOutput(stderr)
	waitErr := cmd.Wait()
	if waitErr != nil {
		panic(waitErr)
	}
}

func main() {
	lambda.Start(HandleRequest)
}

func HandleRequest(ctx context.Context, req structs.CloudWatchEvent) (string, error) {

	var runningOnAws bool = awsUtils.RunningOnAws()
	log.Printf("Running on AWS = %v", runningOnAws)
	// manually setting runningLocally to False will have everything work in the container
	var runningLocally bool = awsUtils.RunningLocally()
	log.Printf("Running locally = %v", runningLocally)
	var coinToPredict string = req.CoinToPredict
	log.Printf("Coin to predict = %v", coinToPredict)
	// set env vars
	awsUtils.SetSsmToEnvVars()

	// Download all the config files
	awsSession := awsUtils.CreateNewAwsSession()
	awsUtils.DownloadFromS3("go-trader", "app/constants.yml", runningOnAws, awsSession)

	// Read in the constants from yaml
	constantsMap := utils.ReadYamlFile("app/constants.yml")

	// Download the rest of the config files
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["actions_to_take_filename"], runningOnAws, awsSession)
	//ml_config.yml
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["ml_config_filename"], runningOnAws, awsSession)
	//trading_state_config.yml
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["trading_state_config_filename"], runningOnAws, awsSession)
	//won_and_lost_amount.yml
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["won_and_lost_amount_filename"], runningOnAws, awsSession)

	// pull new data from FTX with day candles
	granularity, e := strconv.Atoi(constantsMap["candle_granularity"])
	if e != nil {
		panic(e)
	}

	var ftxClient *goftx.Client
	var marketToOrder string
	if coinToPredict == "btc" {
		ftxClient = ftx.NewClient(os.Getenv("BTC_FTX_KEY"), os.Getenv("BTC_FTX_SECRET"), os.Getenv("BTC_SUBACCOUNT_NAME"))

		marketToOrder = "BTC/USD"

	} else if coinToPredict == "eth" {
		ftxClient = ftx.NewClient(os.Getenv("ETH_FTX_KEY"), os.Getenv("ETH_FTX_SECRET"), os.Getenv("ETH_SUBACCOUNT_NAME"))

		marketToOrder = "ETH/USD"
	} else if coinToPredict == "sol" {
		ftxClient = ftx.NewClient(os.Getenv("SOL_FTX_KEY"), os.Getenv("SOL_FTX_SECRET"), os.Getenv("SOL_SUBACCOUNT_NAME"))

		marketToOrder = "SOL/USD"
	}

	currentBitcoinRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["btc_product_code"], granularity)
	currentEthereumRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["eth_product_code"], granularity)
	currentSolRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["sol_product_code"], granularity)
	log.Println(currentSolRecords, "currentSolRecords")
	// currentSpyRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["spy_product_code"], granularity)

	// Add new data to CSV from FTX to s3. This will be used by our Python program

	newestClosePriceBtc, numRecordsWrittenBtc := DownloadUpdateReuploadData(constantsMap["bitcoin_csv_filename"], currentBitcoinRecords, constantsMap, runningOnAws, awsSession)
	log.Println("Records written = ", numRecordsWrittenBtc)

	log.Println(newestClosePriceBtc, "newestClosePriceBtc")

	newestClosePriceEth, numRecordsWrittenEth := DownloadUpdateReuploadData(constantsMap["etherum_csv_filename"], currentEthereumRecords, constantsMap, runningOnAws, awsSession)
	log.Println("Records written = ", numRecordsWrittenEth)
	log.Println(newestClosePriceEth, "newestClosePriceEth")

	newestClosePriceSol, numRecordsWrittenSol := DownloadUpdateReuploadData(constantsMap["sol_csv_filename"], currentSolRecords, constantsMap, runningOnAws, awsSession)
	log.Println("Records written = ", numRecordsWrittenSol)
	log.Println(newestClosePriceSol, "newestClosePriceSol", awsSession)

	// currentSolRecords

	// "newestClosePriceSpy")
	// newestClosePriceEth, newestClosePriceBtc, newestClosePriceSpy := DownloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, currentSpyRecords, constantsMap, awsSession)
	// log.Println(newestClosePriceBtc, "newestClosePriceBtc")
	// log.Println(newestClosePriceEth, "newestClosePriceEth")
	// log.Println(newestClosePriceSpy, "newestClosePriceSpy")

	// Call the Python Program here. This is kinda jank
	if runningLocally {
		log.Printf("Running only golang code locally")
	} else if runningOnAws {
		log.Printf("Calling our Python program with coin = %v", coinToPredict)
		runPythonMlProgram(constantsMap, coinToPredict)
	}
	// Read in the constants  that have been updated from our python ML program. Determine what to do based
	log.Println("Determining actions to take")
	actionsToTakeConstants := utils.ReadNestedYamlFile(constantsMap["actions_to_take_filename"]) // read in nested yaml?
	log.Println(actionsToTakeConstants[coinToPredict]["action_to_take"])
	actionToTake := actionsToTakeConstants[coinToPredict]["action_to_take"]

	// account information

	log.Println("Logging into FTX to get account info")
	subAccount, _ := ftxClient.SubAccounts.GetSubaccountBalances("eth_trading")

	log.Println("Sub Account", subAccount)

	info, err := ftxClient.Account.GetAccountInformation()
	if err != nil {
		panic(err)
	}
	log.Println(info, "info")
	log.Println(info.TotalAccountValue, "TotalAccountValue")
	log.Println(info.TotalPositionSize, "Total position size ")
	log.Println(info.Positions, "Positions")

	// TODO: once FTX allows short leveraged tokens in the US, add this to the short action
	if !runningLocally {
		switch actionToTake {
		case "none":
			log.Printf("Action for coin %v to take = none", coinToPredict)
		case "none_to_none":
			log.Printf("Action for coin %v to take = none_to_none", coinToPredict)
		case "buy_to_none": // liquidate all positions
			log.Printf("Action for coin %v to take = buy_to_none", coinToPredict)
			ftx.SellOrder(ftxClient, marketToOrder)

		case "short_to_none":
			log.Printf("Action for coin %v to take = short_to_none", coinToPredict)
		case "none_to_buy":
			log.Printf("Action for coin %v to take = none_to_buy", coinToPredict)

			log.Println("------")

			size := info.TotalAccountValue.Div(newestClosePriceEth)

			log.Printf("Taking a position worth of size ~%d", size)
			log.Printf("Taking a position worth %d", newestClosePriceEth.Mul(size))

			if err != nil {
				panic(err)
			}

			ftx.PurchaseOrder(ftxClient, size, marketToOrder)

		case "none_to_short":
			log.Printf("Action for coin %v to take = none_to_short", coinToPredict)
		case "buy_to_continue_buy":
			log.Printf("Action for coin %v to take = buy_to_continue_buy.  Leaving everything as is for now", coinToPredict)
		case "short_to_continue_short":
			log.Printf("Action for coin %v to take = short_to_continue_short. Leaving everything as is for now", coinToPredict)
		default:
			panic("We didn't hit a case statement for action to take")
		}
	} else {
		log.Println("Running locally, not taking positions")
	}

	// upload any config changes that we need to maintain state
	if !runningLocally {
		//actions_to_take.yml
		awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["actions_to_take_filename"], runningOnAws, awsSession)
		//constants.yml
		awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["constants_filename"], runningOnAws, awsSession)
		//ml_config.yml
		awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["ml_config_filename"], runningOnAws, awsSession)
		//trading_state_config.yml
		awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["trading_state_config_filename"], runningOnAws, awsSession)
		//won_and_lost_amount.yml
		awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["won_and_lost_amount_filename"], runningOnAws, awsSession)
	} else {
		log.Println("Running locally, not upload config files")
	}

	// send email
	if !runningLocally {
		awsUtils.SendEmail(fmt.Sprintf("Successfully executed go-trader for coin = %v", coinToPredict), constantsMap["log_filename"], runningOnAws)
	} else {
		log.Println("No emails, running locally")
	}
	// all done!
	return "Finished!", nil

}
