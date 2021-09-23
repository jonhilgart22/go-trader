package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"os"

	"github.com/go-numb/go-ftx/auth"
	"github.com/go-numb/go-ftx/rest"

	// "github.com/go-numb/go-ftx/rest/private/orders"
	// "github.com/go-numb/go-ftx/rest/private/account"
	// "github.com/go-numb/go-ftx/rest/public/futures"
	"github.com/go-numb/go-ftx/rest/public/markets"
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

func readYamlFile(fileLocation string) map[string]string {
	fmt.Println(" ")
	yfile, err := ioutil.ReadFile(fileLocation)

	if err != nil {
		panic(err)
	}
	data := make(map[string]string)
	err2 := yaml.Unmarshal(yfile, &data)
	if err2 != nil {
		panic(err)
	}
	for k, v := range data {

		fmt.Printf("%s -> %s\n", k, v)

	}
	fmt.Println("Finished reading in yaml constants")
	fmt.Println(" ")

	return data
}

func downloadUpdateReuploadData(currentBitcoinRecords *markets.ResponseForCandles, currentEthereumRecords *markets.ResponseForCandles, constantsMap map[string]string) {

	// download the files from s3
	fmt.Println("Downloading ", constantsMap["etherum_csv_filename"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"])
	fmt.Println("Downloading ", constantsMap["bitcoin_csv_filename"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"])

	// read the data into memory
	bitcoinRecords := readCsvFile(constantsMap["bitcoin_csv_filename"])
	etherumRecords := readCsvFile(constantsMap["etherum_csv_filename"])

	newestBitcoinDate := csvUtils.FindNewestCsvDate(bitcoinRecords)
	newestEtherumDate := csvUtils.FindNewestCsvDate(etherumRecords)
	fmt.Println(newestBitcoinDate, "newestBitcoinDate")
	fmt.Println(newestEtherumDate, "newestEtherumDate")

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
}

func pullDataFromFtx(productCode string, resolution int) *markets.ResponseForCandles {
	client := rest.New(auth.New(os.Getenv("FTX_KEY"), os.Getenv("FTX_SECRET")))

	records, err := client.Candles(&markets.RequestForCandles{
		ProductCode: productCode,
		Resolution:  resolution,
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Pulled records for", productCode)
	return records
}

func main() {

	// Read in the constants from yaml
	constantsMap := readYamlFile("app/constants.yml")

	// pull new data from FTX with day candles
	currentBitcoinRecords := pullDataFromFtx("BTC/USD", 86400)
	currentEthereumRecords := pullDataFromFtx("ETH/USD", 86400)

	// Add new data to CSV from FTX to s3. This will be used by our Python program
	downloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, constantsMap)

	// Download the model files to be used by the python program
	fmt.Println("Downloadingthe following model files", constantsMap["tcn_model_btc"], constantsMap["tcn_model_eth"], constantsMap["nbeats_model_btc"], constantsMap["nbeats_model_eth"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["tcn_model_btc"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["tcn_model_eth"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["nbeats_model_btc"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["nbeats_model_eth"])

	// Call the Python Program here

	// upload the model files

	// upload any config changes that we need to maintain state

}
