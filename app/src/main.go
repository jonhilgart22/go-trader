package main

import (
	"bufio"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"strconv"

	"path/filepath"

	"github.com/shopspring/decimal"

	"github.com/grishinsana/goftx/models"
	"github.com/jonhilgart22/go-trader/app/csvUtils"
	"github.com/jonhilgart22/go-trader/app/ftx"
	"github.com/jonhilgart22/go-trader/app/s3Utils"
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

func downloadUpdateReuploadData(currentBitcoinRecords []*models.HistoricalPrice, currentEthereumRecords []*models.HistoricalPrice, constantsMap map[string]string) (decimal.Decimal, decimal.Decimal) {

	// download the files from s3
	// TODO: mkdir for data?
	log.Println("Downloading ", constantsMap["etherum_csv_filename"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"])
	log.Println("Downloading ", constantsMap["bitcoin_csv_filename"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"])

	// read the data into memory
	bitcoinRecords := csvUtils.ReadCsvFile(constantsMap["bitcoin_csv_filename"])
	etherumRecords := csvUtils.ReadCsvFile(constantsMap["etherum_csv_filename"])
	// spyRecords := csvUtils.ReadCsvFile(constantsMap["spy_csv_filename"])

	newestBitcoinDate, newestClosePriceBtc := csvUtils.FindNewestData(bitcoinRecords)
	newestEtherumDate, newestClosePriceEth := csvUtils.FindNewestData(etherumRecords)
	// newestSpyDate, newestClosePriceSpy := csvUtils.FindNewestData(spyRecords)
	log.Println(newestBitcoinDate, "newestBitcoinDate")
	log.Println(newestEtherumDate, "newestEtherumDate")
	// log.Println(spyRecords, "spyRecords")

	// add new data as needed
	numBitcoinRecordsWritten := csvUtils.WriteNewCsvData(currentBitcoinRecords, newestBitcoinDate, constantsMap["bitcoin_csv_filename"])
	log.Println("Finished Bitcoin CSV")
	log.Println("Records written = ", numBitcoinRecordsWritten)
	numEtherumRecordsWritten := csvUtils.WriteNewCsvData(currentEthereumRecords, newestEtherumDate, constantsMap["etherum_csv_filename"])
	log.Println("Finished ETH CSV")
	log.Println("Records written = ", numEtherumRecordsWritten)
	// numSpyRecordsWritten := csvUtils.WriteNewCsvData(currentSpyRecords, newestSpyDate, constantsMap["spy_csv_filename"])
	// log.Println("Finished SPY CSV")
	// log.Println("Records written = ", numSpyRecordsWritten)

	// upload back to s3
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"])
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"])
	// s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["spy_csv_filename"])

	return newestClosePriceEth, newestClosePriceBtc
	//newestClosePriceSpy
}

func downloadModelFiles(constantsMap map[string]string) {
	tcnEthModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["tcn_modelname_eth"], constantsMap["tcn_filename_eth"])
	tcnBtcModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["tcn_modelname_btc"], constantsMap["tcn_filename_btc"])

	nbeatsBtcModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["nbeats_modelname_btc"], constantsMap["nbeats_filename_btc"])
	nbeatsEthModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["nbeats_modelname_eth"], constantsMap["nbeats_filename_eth"])

	log.Println("Downloading = ", tcnEthModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], tcnEthModelFilePath)
	log.Println("Downloading = ", tcnBtcModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], tcnBtcModelFilePath)
	log.Println("Downloading = ", nbeatsEthModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], nbeatsEthModelFilePath)
	log.Println("Downloading = ", nbeatsBtcModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], nbeatsBtcModelFilePath)

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

	const coinToPredict string = "btc"
	// Download all the config files
	s3Utils.DownloadFromS3("go-trader", "app/constants.yml")

	// Read in the constants from yaml
	constantsMap := readYamlFile("app/constants.yml")

	// Download the rest of the config files
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["actions_to_take_filename"])
	//ml_config.yml
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["ml_config_filename"])
	//trading_state_config.yml
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["trading_state_config_filename"])
	//won_and_lost_amount.yml
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["won_and_lost_amount_filename"])

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
	newestClosePriceEth, newestClosePriceBtc := downloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, constantsMap)
	log.Println(newestClosePriceBtc, "newestClosePriceBtc")
	log.Println(newestClosePriceEth, "newestClosePriceEth")
	// "newestClosePriceSpy")
	// newestClosePriceEth, newestClosePriceBtc, newestClosePriceSpy := downloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, currentSpyRecords, constantsMap)
	// log.Println(newestClosePriceBtc, "newestClosePriceBtc")
	// log.Println(newestClosePriceEth, "newestClosePriceEth")
	// log.Println(newestClosePriceSpy, "newestClosePriceSpy")

	// Download the model files to be used by the python program
	// models need to be downloaded to models/checkpoints/{model_name}/{filename}
	// TODO: uncomment
	// don't need to do this
	// downloadModelFiles(constantsMap)

	// Call the Python Program here. This is kinda jank
	log.Printf("Calling our Python program with coin = %v", coinToPredict)
	runPythonMlProgram(constantsMap, coinToPredict)

	// Read in the constants  that have been updated from our python ML program. Determine what to do based
	log.Println("Determining actions to take")
	actionsToTakeConstants := readNestedYamlFile(constantsMap["actions_to_take_filename"]) // read in nested yaml?
	log.Println(actionsToTakeConstants[coinToPredict]["action_to_take"])
	actionToTake := actionsToTakeConstants[coinToPredict]["action_to_take"]

	// account informations

	// if coinToPredict == "btc" {
	marketToOrder := "BTC/USD"
	// }
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

		size, err := decimal.NewFromString("0.0001")
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
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["actions_to_take_filename"])
	//constants.yml
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["constants_filename"])
	//ml_config.yml
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["ml_config_filename"])
	//trading_state_config.yml
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["trading_state_config_filename"])
	//won_and_lost_amount.yml
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["won_and_lost_amount_filename"])

	// )

}
