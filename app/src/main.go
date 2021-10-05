package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"time"

	"path/filepath"

	"github.com/shopspring/decimal"

	// "github.com/go-numb/go-ftx/rest/private/orders"

	// "github.com/go-numb/go-ftx/rest/public/futures"

	"github.com/grishinsana/goftx"
	"github.com/grishinsana/goftx/models"
	"github.com/jonhilgart22/go-trader/app/csvUtils"
	"github.com/jonhilgart22/go-trader/app/s3Utils"
	"github.com/jonhilgart22/go-trader/app/structs"
	"gopkg.in/yaml.v3"
)

func readCsvFile(filePath string) []structs.HistoricCandles {
	f, err := os.Open(filePath)
	if err != nil {
		panic(err)
	}
	reader := csv.NewReader(bufio.NewReader(f))
	defer f.Close()

	records := []structs.HistoricCandles{}

	for {
		line, error := reader.Read()
		if error == io.EOF {
			break
		} else if error != nil {
			panic(error)
		} else if csvUtils.Contains(line, "date") && csvUtils.Contains(line, "open") && csvUtils.Contains(line, "close") {
			continue
		}
		records = append(records, structs.HistoricCandles{
			Date:  csvUtils.ParseDate(line[0]),
			Open:  csvUtils.ConvertStringToFloat(line[1]),
			High:  csvUtils.ConvertStringToFloat(line[2]),
			Low:   csvUtils.ConvertStringToFloat(line[3]),
			Close: csvUtils.ConvertStringToFloat(line[4]),
		})
	}

	return records
}

func readNestedYamlFile(fileLocation string) map[string]map[string]string {
	fmt.Println(" ")
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
		fmt.Println("Finished reading in yaml constants")
		fmt.Println(" ")
	}
	return doubleLevelData
}

func readYamlFile(fileLocation string) map[string]string {
	fmt.Println(" ")
	yfile, err := ioutil.ReadFile(fileLocation)

	if err != nil {
		panic(err)
	}
	singleLevelData := make(map[string]string)

	errSingle := yaml.Unmarshal(yfile, &singleLevelData)
	if errSingle != nil {
		fmt.Println("Signle level didn't work, test two levels")
	} else {
		for k, v := range singleLevelData {

			fmt.Printf("%s -> %s\n", k, v)

		}
		fmt.Println("Finished reading in yaml constants")
		fmt.Println(" ")
	}
	return singleLevelData

}

func downloadUpdateReuploadData(currentBitcoinRecords []*models.HistoricalPrice, currentEthereumRecords []*models.HistoricalPrice, constantsMap map[string]string) (decimal.Decimal, decimal.Decimal) {

	// download the files from s3
	// TODO: mkdir for data?
	fmt.Println("Downloading ", constantsMap["etherum_csv_filename"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"])
	fmt.Println("Downloading ", constantsMap["bitcoin_csv_filename"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"])

	// read the data into memory
	bitcoinRecords := readCsvFile(constantsMap["bitcoin_csv_filename"])
	etherumRecords := readCsvFile(constantsMap["etherum_csv_filename"])

	newestBitcoinDate, newestClosePriceBtc := csvUtils.FindNewestData(bitcoinRecords)
	newestEtherumDate, newestClosePriceEth := csvUtils.FindNewestData(etherumRecords)
	fmt.Println(newestBitcoinDate, "newestBitcoinDate")
	fmt.Println(newestEtherumDate, "newestEtherumDate")
	fmt.Println(newestClosePriceBtc, "newestClosePriceBtc")
	fmt.Println(newestClosePriceEth, "newestClosePriceEth")

	// add new data as needed
	numBitcoinRecordsWritten := csvUtils.WriteNewCsvData(currentBitcoinRecords, newestBitcoinDate, constantsMap["bitcoin_csv_filename"])
	fmt.Println("Finished Bitcoin CSV")
	fmt.Println("Records written = ", numBitcoinRecordsWritten)
	numEtherumRecordsWritten := csvUtils.WriteNewCsvData(currentEthereumRecords, newestEtherumDate, constantsMap["etherum_csv_filename"])
	fmt.Println("Finished Etherum CSV")
	fmt.Println("Records written = ", numEtherumRecordsWritten)

	// upload back to s3
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"])
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"])

	return newestClosePriceEth, newestClosePriceBtc
}

func PtrInt(i int) *int {
	return &i
}

func pullDataFromFtx(productCode string, resolution int) []*models.HistoricalPrice {
	client := goftx.New(
		goftx.WithAuth(os.Getenv("FTX_KEY"), os.Getenv("FTX_SECRET"), os.Getenv("BTC_SUBACCOUNT_NAME")),
		goftx.WithHTTPClient(&http.Client{
			Timeout: 5 * time.Second,
		}),
	)

	records, err := client.Markets.GetHistoricalPrices(productCode, &models.GetHistoricalPricesParams{
		Resolution: models.Day,
		StartTime:  PtrInt(int(time.Now().Add(-7 * 86400 * time.Second).Unix())), // last 7 days
		EndTime:    PtrInt(int(time.Now().Unix())),
	})

	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Pulled records for", productCode)
	fmt.Println("Records =", records)
	return records
}

func downloadModelFiles(constantsMap map[string]string) {
	tcnEthModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["tcn_modelname_eth"], constantsMap["tcn_filename_eth"])
	tcnBtcModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["tcn_modelname_btc"], constantsMap["tcn_filename_btc"])

	nbeatsBtcModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["nbeats_modelname_btc"], constantsMap["nbeats_filename_btc"])
	nbeatsEthModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["nbeats_modelname_eth"], constantsMap["nbeats_filename_eth"])

	fmt.Println("Downloading = ", tcnEthModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], tcnEthModelFilePath)
	fmt.Println("Downloading = ", tcnBtcModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], tcnBtcModelFilePath)
	fmt.Println("Downloading = ", nbeatsEthModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], nbeatsEthModelFilePath)
	fmt.Println("Downloading = ", nbeatsBtcModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], nbeatsBtcModelFilePath)

}

func copyOutput(r io.Reader) {
	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		fmt.Println(scanner.Text())
	}
}

func runPythonMlProgram(constantsMap map[string]string) {
	pwd, err := os.Getwd()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	fmt.Println("Current working directory = ", pwd)

	cmd := exec.Command("python", filepath.Join(pwd, constantsMap["python_script_path"]))
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		panic(err)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		panic(err)
	}
	err = cmd.Start()
	if err != nil {
		panic(err)
	}

	go copyOutput(stdout)
	go copyOutput(stderr)
	cmd.Wait()

}

func main() {

	const coinToPredict string = "btc"

	// Read in the constants from yaml
	constantsMap := readYamlFile("app/constants.yml")

	// pull new data from FTX with day candles
	granularity, e := strconv.Atoi(constantsMap["candle_granularity"])
	if e != nil {
		panic(e)
	}
	currentBitcoinRecords := pullDataFromFtx(constantsMap["btc_product_code"], granularity)
	currentEthereumRecords := pullDataFromFtx(constantsMap["eth_product_code"], granularity)

	// Add new data to CSV from FTX to s3. This will be used by our Python program
	downloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, constantsMap)

	// Download the model files to be used by the python program
	// models need to be downloaded to models/checkpoints/{model_name}/{filename}
	// TODO: uncomment
	// don't need to do this
	// downloadModelFiles(constantsMap)

	// Call the Python Program here. This is kinda jank
	fmt.Println("Calling our Python program")

	// runPythonMlProgram(constantsMap)

	// Read in the constants  that have been updated from our python ML program. Determine what to do based
	fmt.Println("Determining actions to take")
	actionsToTakeConstants := readNestedYamlFile("app/actions_to_take.yml") // read in nested yaml?
	fmt.Println(actionsToTakeConstants[coinToPredict]["action_to_take"])
	actionToTake := actionsToTakeConstants[coinToPredict]["action_to_take"]

	switch actionToTake {
	case "none":
		fmt.Printf("Action for coin %v to take = none", coinToPredict)
	case "none_to_none":
		fmt.Printf("Action for coin %v to take = none_to_non", coinToPredict)
	case "buy_to_none":
		fmt.Printf("Action for coin %v to take = buy_to_none", coinToPredict)
	case "short_to_none":
		fmt.Printf("Action for coin %v to take = short_to_none", coinToPredict)
	case "none_to_buy":
		fmt.Printf("Action for coin %v to take = none_to_buy", coinToPredict)
	case "none_to_short":
		fmt.Printf("Action for coin %v to take = none_to_short", coinToPredict)
	case "buy_to_continue_buy":
		fmt.Printf("Action for coin %v to take = buy_to_continue_buy.  Leaving everything as is for now", coinToPredict)
	case "short_to_continue_short":
		fmt.Printf("Action for coin %v to take = short_to_continue_short. Leaving everything as is for now", coinToPredict)
	default:
		panic("We didn't hit a case statement for action to take")
	}

	// account informations
	// client or clientWithSubAccounts in this time.

	client := goftx.New(
		goftx.WithAuth(os.Getenv("BTC_FTX_KEY"), os.Getenv("BTC_FTX_SECRET"), os.Getenv("BTC_SUBACCOUNT_NAME")),
		goftx.WithFTXUS(),
	)

	// if coinToPredict == "btc" {
	marketToOrder := "BTC/USD"
	// }
	info, err := client.Account.GetAccountInformation()
	if err != nil {
		panic(err)
	}
	fmt.Println(info, "info")
	fmt.Println(info.TotalAccountValue, "TotalAccountValue")

	// upload any config changes that we need to maintain state

	// TODO: add in stop loss order with any buys

	size, err := decimal.NewFromString(".000001")
	if err != nil {
		panic(err)
	}

	order, err := client.PlaceOrder(&models.PlaceOrderPayload{
		Market: marketToOrder,
		Side:   "buy",
		Size:   size,
		Type:   "market",
	})
	if err != nil {
		panic(err)
	}
	fmt.Println(order, "Order")

	// STOP LOSS ORDER
	// client.PlaceTriggerOrder(&models.PlaceTriggerOrderPayload{
	// 	Market: marketToOrder,
	// 	Side: "sell",
	// 	Size: size,
	// 	Type: "trailingStop",
	// 	trailValue: "" // 5% of the current price?

	// })

	// upload any config changes that we need to maintain state

	// )

}
