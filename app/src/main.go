package main

import (
	"context"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/shopspring/decimal"

	"github.com/grishinsana/goftx"
	"github.com/grishinsana/goftx/models"
	"github.com/jonhilgart22/go-trader/app/awsUtils"
	"github.com/jonhilgart22/go-trader/app/ftx"
	"github.com/jonhilgart22/go-trader/app/structs"
	"github.com/jonhilgart22/go-trader/app/utils"
	"github.com/jonhilgart22/go-trader/app/yahoo"
)

func main() {
	lambda.Start(HandleRequest)
}

func HandleRequest(ctx context.Context, req structs.CloudWatchEvent) (string, error) {

	start := time.Now() // time how long execution takes. 15 min timeout AWS lambda

	var runningOnAws bool = awsUtils.RunningOnAws()
	log.Printf("Running on AWS = %v", runningOnAws)
	// manually setting runningLocally to False will have everything work in the container
	var runningLocally bool = awsUtils.RunningLocally()
	log.Printf("Running locally = %v", runningLocally)
	var coinToPredict string = strings.ToLower(req.CoinToPredict)
	log.Printf("Coin to predict = %v", coinToPredict)

	if !utils.StringInSlice(coinToPredict, []string{"btc", "eth", "sol", "matic", "link"}) {
		log.Fatal("incorrect coinToPredict = ", coinToPredict)
	}
	// set env vars
	awsUtils.SetSsmToEnvVars()

	// Download all the config files
	awsSession := awsUtils.CreateNewAwsSession()
	awsUtils.DownloadFromS3("go-trader", "tmp/constants.yml", runningOnAws, awsSession)

	// Read in the constants from yaml
	// 0 so that we don't alter the filename
	constantsMap := utils.ReadYamlFile("tmp/constants.yml", runningOnAws, "0")

	// Download the rest of the config files
	DownloadConfigFiles(constantsMap, runningOnAws, awsSession, coinToPredict)

	// pull new data from FTX with day candles
	granularity, e := strconv.Atoi(constantsMap["candle_granularity"])
	if e != nil {
		panic(e)
	}

	ftxClient, marketToOrder := CreateFtxClientAndMarket(coinToPredict)
	// ftx
	currentBitcoinRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["btc_product_code"], granularity)
	currentEthereumRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["eth_product_code"], granularity)
	currentSolRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["sol_product_code"], granularity)
	currentMaticRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["matic_product_code"], granularity)
	currentLinkRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["link_product_code"], granularity)
	// yahoo
	currentTbtRecords := yahoo.PullDataFromYahoo(constantsMap["tbt_product_code"])
	log.Println(currentTbtRecords, "currentTbtRecords")
	// currentSpyRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["spy_product_code"], granularity)

	// Add new data to CSV from FTX/yahoo to s3. This will be used by our Python program

	newestClosePriceBtc, numRecordsWrittenBtc := DownloadUpdateData(constantsMap["bitcoin_csv_filename"], currentBitcoinRecords, constantsMap, runningOnAws, awsSession)
	log.Println("Records written = ", numRecordsWrittenBtc)

	log.Println(newestClosePriceBtc, "newestClosePriceBtc")

	newestClosePriceEth, numRecordsWrittenEth := DownloadUpdateData(constantsMap["etherum_csv_filename"], currentEthereumRecords, constantsMap, runningOnAws, awsSession)
	log.Println("Records written = ", numRecordsWrittenEth)
	log.Println(newestClosePriceEth, "newestClosePriceEth")

	newestClosePriceSol, numRecordsWrittenSol := DownloadUpdateData(constantsMap["sol_csv_filename"], currentSolRecords, constantsMap, runningOnAws, awsSession)
	log.Println("Records written = ", numRecordsWrittenSol)
	log.Println(newestClosePriceSol, "newestClosePriceSol", awsSession)

	newestClosePriceMatic, numRecordsWrittenMatic := DownloadUpdateData(constantsMap["matic_csv_filename"], currentMaticRecords, constantsMap, runningOnAws, awsSession)
	log.Println("Records written = ", numRecordsWrittenMatic)
	log.Println(newestClosePriceMatic, "newestClosePriceMatic", awsSession)

	newestClosePriceLink, numRecordsWrittenLink := DownloadUpdateData(constantsMap["link_csv_filename"], currentLinkRecords, constantsMap, runningOnAws, awsSession)
	log.Println("Records written = ", numRecordsWrittenLink)
	log.Println(newestClosePriceLink, "newestClosePriceLink", awsSession)

	newestClosePriceTbt, numRecordsWrittenTbt := DownloadUpdateData(constantsMap["tbt_csv_filename"], currentTbtRecords, constantsMap, runningOnAws, awsSession)
	log.Println("Records written = ", numRecordsWrittenTbt)
	log.Println(newestClosePriceTbt, "newestClosePriceTbt", awsSession)

	// Call the Python Program here. This is kinda jank
	if runningLocally {
		log.Printf("Running only golang code locally")
	} else if runningOnAws {
		log.Printf("Calling our Python program with coin = %v", coinToPredict)
		RunPythonMlProgram(constantsMap, coinToPredict)
	}
	// Read in the constants  that have been updated from our python ML program. Determine what to do based
	log.Println("Determining actions to take")
	// only updated the tmp./ folder
	actionsToTakeConstants := utils.ReadYamlFile(constantsMap["actions_to_take_filename"], runningOnAws, coinToPredict)
	// read in nested yaml?
	actionToTake := actionsToTakeConstants["action_to_take"]
	log.Println(actionToTake, "actionToTake")

	log.Println("Logging into FTX to get account info")

	info, err := ftxClient.Account.GetAccountInformation()
	if err != nil {
		log.Println("Issue with authenticating to FTX")
		panic(err)
	}
	log.Println(info, "info")
	log.Println(info.TotalAccountValue, "TotalAccountValue")
	log.Println(info.TotalPositionSize, "Total position size ")
	log.Println(info.Positions, "Positions")

	// TODO: once FTX allows short leveraged tokens in the US, add this to the short action
	log.Println("default_purchase_size", constantsMap["default_purchase_size"])
	sizeToBuy, err := decimal.NewFromString(constantsMap["default_purchase_size"])
	if err != nil {
		panic(err)
	}

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

			if coinToPredict == "btc" {
				sizeToBuy = info.TotalAccountValue.Div(newestClosePriceBtc)
			} else if coinToPredict == "eth" {
				sizeToBuy = info.TotalAccountValue.Div(newestClosePriceEth)
			} else if coinToPredict == "sol" {
				sizeToBuy = info.TotalAccountValue.Div(newestClosePriceSol)
			} else if coinToPredict == "matic" {
				sizeToBuy = info.TotalAccountValue.Div(newestClosePriceMatic)
			} else if coinToPredict == "link" {
				sizeToBuy = info.TotalAccountValue.Div(newestClosePriceLink)
			}

			log.Println("Taking a position worth of sizeToBuy ~", sizeToBuy)
			log.Println("Taking a position worth ", newestClosePriceEth.Mul(sizeToBuy))

			if err != nil {
				panic(err)
			}

			ftx.PurchaseOrder(ftxClient, sizeToBuy, marketToOrder)

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
		IterateAndUploadTmpFilesYmlCsv("/tmp/", constantsMap, runningOnAws, awsSession)
	} else {
		log.Println("running locally, no tmp uploads")
	}

	// send email
	defaultPurchaseSize, err := decimal.NewFromString(constantsMap["default_purchase_size"])
	if err != nil {
		panic(err)
	}

	elapsed := time.Since(start)

	if !runningLocally {
		awsUtils.SendEmail(fmt.Sprintf("Successfully executed go-trader for coin = %v", coinToPredict), constantsMap["log_filename"], sizeToBuy, runningOnAws, constantsMap["email_separator"], defaultPurchaseSize, elapsed.Minutes())
	} else {
		log.Println("No emails, running locally")
	}
	// all done!
	return "Finished!", nil

}

func IterateAndUploadTmpFilesYmlCsv(path string, constantsMap map[string]string, runningOnAws bool, awsSession *session.Session) {

	files, err := ioutil.ReadDir(path)
	if err != nil {
		log.Fatal(err)
	}

	for _, f := range files {

		if strings.Contains(f.Name(), "yml") || strings.Contains(f.Name(), "csv") {
			if !runningOnAws {
				log.Println("Not uploading to S3, running locally")
			} else {
				// all the config files are in the same folder under tmp. Because we are iterating all files in the "/tmp/" directory, the "tmp" is removed from the filename. So we need to add it back.
				finalFilename := "tmp/" + f.Name()
				fmt.Println("uploadFilename - ", finalFilename)
				awsUtils.UploadToS3(constantsMap["s3_bucket"], finalFilename, runningOnAws, awsSession)
			}
		}
	}

}

func DownloadUpdateData(csvFilename string, inputRecords []*models.HistoricalPrice, constantsMap map[string]string, runningOnAws bool, s3Client *session.Session) (decimal.Decimal, int) {

	// download the files from s3
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], csvFilename, runningOnAws, s3Client)
	// read the data into memory
	records := utils.ReadCsvFile(csvFilename, runningOnAws)
	newestDate, newestClosePrice := utils.FindNewestData(records)
	log.Println(newestClosePrice, "newestClosePrice")
	log.Println(newestDate, "newestDate")
	loc, _ := time.LoadLocation("America/Los_Angeles")
	todaysTime := time.Now().In(loc).Truncate(24 * time.Hour)
	yesterdaysTime := todaysTime.AddDate(0, 0, -1)

	// print the current time truncated to the current date

	log.Println("time.Now().In(loc).Day()", time.Now().In(loc).Truncate(24*time.Hour).Day())

	// add new data as needed
	numRecordsWritten, newestWrittenDate := utils.WriteNewCsvData(inputRecords, newestDate, csvFilename, runningOnAws)
	log.Println(numRecordsWritten, "numRecordsWritten inside of DownloadUpdateData")

	// compare the date to todays date and if it is the same, then we don't need to do anything. Truncate to the day
	testingDate := time.Date(2017, time.Month(1), 5, 0, 0, 0, 0, time.UTC)
	log.Println("testingDate.Day()", testingDate.Day())
	log.Println("newestWrittenDate.Day() ", newestWrittenDate.Day())
	log.Println("yesterdaysTime.Day() ", yesterdaysTime.Day())
	log.Println("todaysTime.Day() ", todaysTime.Day())
	// kinda jank, but if we are testing, check the date in main_test.go. TODO: refactor to use interface
	_, localEnvVarPresent := os.LookupEnv("ON_LOCAL")
	if newestWrittenDate.Day() == testingDate.Day() {
		log.Println("Testing")
	} else if localEnvVarPresent {
		log.Println("Running on local")
	} else if newestWrittenDate.Day() == todaysTime.Day() {
		log.Println("Must be testing the lambda on off times.")
	} else if newestWrittenDate.Day() != yesterdaysTime.Day() {
		log.Fatal("Newest date is not yesterday's date or todays date. Something is off with downloading data")
		panic("Newest date is not yesterday's date. Something is off with downloading data")
	}

	return newestClosePrice, numRecordsWritten

}

func RunPythonMlProgram(constantsMap map[string]string, coinToPredict string) {
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

func DownloadConfigFiles(constantsMap map[string]string, runningOnAws bool, awsSession *session.Session, coinToPredict string) {
	// only download the configs for the coin we are predicting
	splitStringsActionsToTake := strings.Split(constantsMap["actions_to_take_filename"], "/")
	actionsToTakeFilename := splitStringsActionsToTake[0] + "/" + coinToPredict + "_" + splitStringsActionsToTake[1]
	log.Println("actionsToTakeFilename = ", actionsToTakeFilename)

	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], actionsToTakeFilename, runningOnAws, awsSession)

	//ml_config.yml
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["ml_config_filename"], runningOnAws, awsSession)
	//trading_state_config.yml
	splitStringsTradingState := strings.Split(constantsMap["trading_state_config_filename"], "/")
	tradingStateConfigFilename := splitStringsTradingState[0] + "/" + coinToPredict + "_" + splitStringsTradingState[1]

	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], tradingStateConfigFilename, runningOnAws, awsSession)
	//won_and_lost_amount.yml
	splitStringsWonLost := strings.Split(constantsMap["won_and_lost_amount_filename"], "/")
	WonLostConfigFilename := splitStringsWonLost[0] + "/" + coinToPredict + "_" + splitStringsWonLost[1]

	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], WonLostConfigFilename, runningOnAws, awsSession)

	// predictions_csv
	splitStringsPredictions := strings.Split(constantsMap["all_predictions_csv_filename"], "/")
	AllPredictionsFilename := splitStringsPredictions[0] + "/" + coinToPredict + "_" + splitStringsPredictions[1]
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], AllPredictionsFilename, runningOnAws, awsSession)
}

func CreateFtxClientAndMarket(coinToPredict string) (*goftx.Client, string) {

	coinToPredictUpper := strings.ToUpper(coinToPredict)
	ftxKey := coinToPredictUpper + "_FTX_KEY"
	log.Println("ftxKey = ", ftxKey)
	ftxSecret := coinToPredictUpper + "_FTX_SECRET"
	log.Println("ftxSecret = ", ftxSecret)
	subAcccountName := coinToPredictUpper + "_SUBACCOUNT_NAME"
	log.Println("subAcccountName = ", subAcccountName)
	log.Println("ftxKey = ", ftxKey)
	log.Println("ftxSecret = ", ftxSecret)

	ftxClient := ftx.NewClient(os.Getenv(ftxKey), os.Getenv(ftxSecret), os.Getenv(subAcccountName))

	marketToOrder := coinToPredictUpper + "/USD"
	log.Println("marketToOrder = ", marketToOrder)

	return ftxClient, marketToOrder

}
