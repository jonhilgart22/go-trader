package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"strconv"

	"path/filepath"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/shopspring/decimal"

	"github.com/aws/aws-lambda-go/events"
	"github.com/grishinsana/goftx/models"
	"github.com/jonhilgart22/go-trader/app/awsUtils"
	"github.com/jonhilgart22/go-trader/app/csvUtils"
	"github.com/jonhilgart22/go-trader/app/ftx"
	"github.com/jonhilgart22/go-trader/app/structs"
	"gopkg.in/yaml.v3"
)

func readNestedYamlFile(fileLocation string) map[string]map[string]string {
	log.Println(" ")
	yfile, err := ioutil.ReadFile(fileLocation)

	if err != nil {
		panic(err)
	}
	doubleLevelData := make(map[string]map[string]string)
	errDouble := yaml.Unmarshal(yfile, &doubleLevelData)
	if errDouble != nil {
		panic(errDouble)
	} else {
		for k, v := range doubleLevelData {

			fmt.Printf("%s -> %s\n", k, v)

		}
		log.Println("Finished reading in yaml constants")
		log.Println(" ")
	}
	return doubleLevelData
}

func readYamlFile(fileLocation string) map[string]string {
	log.Println(" ")
	yfile, err := ioutil.ReadFile(fileLocation)

	if err != nil {
		panic(err)
	}
	singleLevelData := make(map[string]string)

	errSingle := yaml.Unmarshal(yfile, &singleLevelData)
	if errSingle != nil {
		log.Println("Signle level didn't work, test two levels")
	} else {
		for k, v := range singleLevelData {

			fmt.Printf("%s -> %s\n", k, v)

		}
		log.Println("Finished reading in yaml constants")
		log.Println(" ")
	}
	return singleLevelData

}

func downloadUpdateReuploadData(currentBitcoinRecords []*models.HistoricalPrice, currentEthereumRecords []*models.HistoricalPrice, constantsMap map[string]string, runningOnAws bool) (decimal.Decimal, decimal.Decimal) {

	// download the files from s3
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"], runningOnAws)
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"], runningOnAws)

	// read the data into memory
	bitcoinRecords := csvUtils.ReadCsvFile(constantsMap["bitcoin_csv_filename"], runningOnAws)
	etherumRecords := csvUtils.ReadCsvFile(constantsMap["etherum_csv_filename"], runningOnAws)
	// spyRecords := csvUtils.ReadCsvFile(constantsMap["spy_csv_filename"])

	newestBitcoinDate, newestClosePriceBtc := csvUtils.FindNewestData(bitcoinRecords)
	newestEtherumDate, newestClosePriceEth := csvUtils.FindNewestData(etherumRecords)
	// newestSpyDate, newestClosePriceSpy := csvUtils.FindNewestData(spyRecords)
	log.Println(newestBitcoinDate, "newestBitcoinDate")
	log.Println(newestEtherumDate, "newestEtherumDate")
	// log.Println(spyRecords, "spyRecords")

	// add new data as needed
	numBitcoinRecordsWritten := csvUtils.WriteNewCsvData(currentBitcoinRecords, newestBitcoinDate, constantsMap["bitcoin_csv_filename"], runningOnAws)
	log.Println("Finished Bitcoin CSV")
	log.Println("Records written = ", numBitcoinRecordsWritten)
	numEtherumRecordsWritten := csvUtils.WriteNewCsvData(currentEthereumRecords, newestEtherumDate, constantsMap["etherum_csv_filename"], runningOnAws)
	log.Println("Finished ETH CSV")
	log.Println("Records written = ", numEtherumRecordsWritten)
	// numSpyRecordsWritten := csvUtils.WriteNewCsvData(currentSpyRecords, newestSpyDate, constantsMap["spy_csv_filename"])
	// log.Println("Finished SPY CSV")
	// log.Println("Records written = ", numSpyRecordsWritten)

	// upload back to s3
	awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"], runningOnAws)
	awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"], runningOnAws)
	// awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["spy_csv_filename"])

	return newestClosePriceEth, newestClosePriceBtc
	//newestClosePriceSpy
}

func copyOutput(r io.Reader) {
	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		log.Println(scanner.Text())
	}
}

func runPythonMlProgram(constantsMap map[string]string, coinToPredict string) {
	pwd, err := os.Getwd()
	if err != nil {
		log.Println(err)
		os.Exit(1)
	}
	log.Println("Current working directory = ", pwd)

	cmd := exec.Command("python", filepath.Join(pwd, constantsMap["python_script_path"]), fmt.Sprintf("--coin_to_predict=%v", coinToPredict))
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

	go copyOutput(stdout)
	go copyOutput(stderr)
	cmd.Wait()
}

func main() {
	lambda.Start(HandleRequest)
}

func HandleRequest(ctx context.Context, jsonEvent events.CloudWatchEvent) (string, error) {

	var eventDetails structs.CloudWatchEventDetails

	//Unmarshall the CloudWatchEvent Struct Details
	// err := json.Unmarshal(jsonEvent.Detail, &eventDetails)
	// if err != nil {
	// 	log.Fatal("Could not unmarshal scheduled event: ", err)
	// 	fmt.Println("Could not unmarshal scheduled event: ", err)
	// }
	outputJSON, err := json.Marshal(eventDetails)
	if err != nil {
		log.Fatal("Could not unmarshal scheduled event: ", err)
		fmt.Println("Could not unmarshal scheduled event: ", err)
	}

	fmt.Println("This is the JSON for event details", string(outputJSON))

	var runningOnAws bool = awsUtils.RunningOnAws()
	const coinToPredict string = "btc"
	// set env vars
	awsUtils.SetSsmToEnvVars()

	// Download all the config files
	awsUtils.DownloadFromS3("go-trader", "app/constants.yml", runningOnAws)

	// Read in the constants from yaml
	constantsMap := readYamlFile("app/constants.yml")

	// Download the rest of the config files
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["actions_to_take_filename"], runningOnAws)
	//ml_config.yml
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["ml_config_filename"], runningOnAws)
	//trading_state_config.yml
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["trading_state_config_filename"], runningOnAws)
	//won_and_lost_amount.yml
	awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["won_and_lost_amount_filename"], runningOnAws)

	// pull new data from FTX with day candles
	granularity, e := strconv.Atoi(constantsMap["candle_granularity"])
	if e != nil {
		panic(e)
	}
	ftxClientBtc := ftx.NewClient(os.Getenv("BTC_FTX_KEY"), os.Getenv("BTC_FTX_SECRET"), os.Getenv("BTC_SUBACCOUNT_NAME"))

	currentBitcoinRecords := ftx.PullDataFromFtx(ftxClientBtc, constantsMap["btc_product_code"], granularity)
	currentEthereumRecords := ftx.PullDataFromFtx(ftxClientBtc, constantsMap["eth_product_code"], granularity)
	// currentSpyRecords := ftx.PullDataFromFtx(ftxClientBtc, constantsMap["spy_product_code"], granularity)

	// Add new data to CSV from FTX to s3. This will be used by our Python program
	newestClosePriceEth, newestClosePriceBtc := downloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, constantsMap, runningOnAws)
	log.Println(newestClosePriceBtc, "newestClosePriceBtc")
	log.Println(newestClosePriceEth, "newestClosePriceEth")
	// "newestClosePriceSpy")
	// newestClosePriceEth, newestClosePriceBtc, newestClosePriceSpy := downloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, currentSpyRecords, constantsMap)
	// log.Println(newestClosePriceBtc, "newestClosePriceBtc")
	// log.Println(newestClosePriceEth, "newestClosePriceEth")
	// log.Println(newestClosePriceSpy, "newestClosePriceSpy")

	// Call the Python Program here. This is kinda jank
	_, runningLocally := os.LookupEnv(("ON_LOCAL"))
	if runningLocally {
		log.Printf("Running only golang code locally")
	} else if runningOnAws {
		log.Printf("Calling our Python program with coin = %v", coinToPredict)
		runPythonMlProgram(constantsMap, coinToPredict)
	}
	// Read in the constants  that have been updated from our python ML program. Determine what to do based
	log.Println("Determining actions to take")
	actionsToTakeConstants := readNestedYamlFile(constantsMap["actions_to_take_filename"]) // read in nested yaml?
	log.Println(actionsToTakeConstants[coinToPredict]["action_to_take"])
	actionToTake := actionsToTakeConstants[coinToPredict]["action_to_take"]

	// account informations

	// if coinToPredict == "btc" {
	marketToOrder := "BTC/USD"
	// }
	log.Println("Logging into FTX to get account info")
	info, err := ftxClientBtc.Account.GetAccountInformation()
	if err != nil {
		panic(err)
	}
	log.Println(info, "info")
	log.Println(info.TotalAccountValue, "TotalAccountValue")
	log.Println(info.TotalPositionSize, "Total position size ")
	log.Println(info.Positions, "Positions")

	// TODO: once FTX allows short leveraged tokens in the US, add this to the short action
	switch actionToTake {
	case "none":
		log.Printf("Action for coin %v to take = none", coinToPredict)
	case "none_to_none":
		log.Printf("Action for coin %v to take = none_to_none", coinToPredict)
	case "buy_to_none": // liquidate all positions
		log.Printf("Action for coin %v to take = buy_to_none", coinToPredict)
		ftx.SellOrder(ftxClientBtc, marketToOrder)

	case "short_to_none":
		log.Printf("Action for coin %v to take = short_to_none", coinToPredict)
	case "none_to_buy":
		log.Printf("Action for coin %v to take = none_to_buy", coinToPredict)

		log.Println("------")

		// TODO: update this with correct sizing
		size, err := decimal.NewFromString("0.001")
		log.Println("Taking a position worth ~", size.Mul(newestClosePriceBtc))
		if err != nil {
			panic(err)
		}

		ftx.PurchaseOrder(ftxClientBtc, size, marketToOrder)

	case "none_to_short":
		log.Printf("Action for coin %v to take = none_to_short", coinToPredict)
	case "buy_to_continue_buy":
		log.Printf("Action for coin %v to take = buy_to_continue_buy.  Leaving everything as is for now", coinToPredict)
	case "short_to_continue_short":
		log.Printf("Action for coin %v to take = short_to_continue_short. Leaving everything as is for now", coinToPredict)
	default:
		panic("We didn't hit a case statement for action to take")
	}

	// upload any config changes that we need to maintain state
	//actions_to_take.yml
	awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["actions_to_take_filename"], runningOnAws)
	//constants.yml
	awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["constants_filename"], runningOnAws)
	//ml_config.yml
	awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["ml_config_filename"], runningOnAws)
	//trading_state_config.yml
	awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["trading_state_config_filename"], runningOnAws)
	//won_and_lost_amount.yml
	awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["won_and_lost_amount_filename"], runningOnAws)

	// send email
	awsUtils.SendEmail(fmt.Sprintf("Successfully executed go-trader for coin = %v", coinToPredict))
	// all done!
	return "Finished!", nil

}
