package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"log"
	"os"
	"time"

	"github.com/go-numb/go-ftx/auth"
	"github.com/go-numb/go-ftx/rest"

	// "github.com/go-numb/go-ftx/rest/private/orders"
	// "github.com/go-numb/go-ftx/rest/private/account"
	// "github.com/go-numb/go-ftx/rest/public/futures"
	"github.com/go-numb/go-ftx/rest/public/markets"
	"github.com/jonhilgart22/go-trader/go_app/csvUtils"
	"github.com/jonhilgart22/go-trader/go_app/s3Utils"
	"github.com/jonhilgart22/go-trader/go_app/structs"
)

func readCsvFile(filePath string) []historicCandles {
	f, err := os.Open(filePath)
	if err != nil {
		panic(err)
	}
	reader := csv.NewReader(bufio.NewReader(f))
	defer f.Close()

	records := []historicCandles{}

	for {
		line, error := reader.Read()
		if error == io.EOF {
			break
		} else if error != nil {
			panic(error)
		} else if csvUtils.Contains(line, "date") && csvUtils.Contains(line, "open") && csvUtils.Contains(line, "close") {
			continue
		}
		records = append(records, historicCandles{
			Date:  csvUtils.ParseDate(line[0]),
			Open:  csvUtils.ConvertStringToFloat(line[1]),
			High:  csvUtils.ConvertStringToFloat(line[2]),
			Low:   csvUtils.ConvertStringToFloat(line[3]),
			Close: csvUtils.ConvertStringToFloat(line[4]),
		})
	}

	return records
}



func DownloadAndUpdateCsvData() {

	// open csv file, add new candles to the .csv
	const bitcoinFileName string = "./data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021 copy.csv"
	const etherumFileName string = "./data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv"
	const s3Bucket string = "go-trader"
	const s3EtherumItem string = "data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv"
	const s3BitcoinItem string = "data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021 copy.csv"

	// download the files from s3
	s3Utils.DownloadFromS3(s3Bucket, s3EtherumItem)
	s3Utils.DownloadFromS3(s3Bucket, s3BitcoinItem)

	// read the data into memory
	bitcoinRecords := readCsvFile(bitcoinFileName)
	etherumRecords := readCsvFile(etherumFileName)

	newestBitcoinDate := FindNewestCsvDate(bitcoinRecords)
	newestEtherumDate := FindNewestCsvDate(etherumRecords)
	fmt.Println(newestBitcoinDate, "newestBitcoinDate")
	fmt.Println(newestEtherumDate, "newestEtherumDate")

	// add new data as needed
	numBitcoinRecordsWritten := csvUtils.WriteNewCsvData(currentBitcoinRecords, newestBitcoinDate, bitcoinFileName)
	fmt.Println("Finished Bitcoin CSV")
	fmt.Println("Records written = ", numBitcoinRecordsWritten)
	numEtherumRecordsWritten := csvUtils.WriteNewCsvData(currentEthereumRecords, newestEtherumDate, etherumFileName)
	fmt.Println("Finished Etherum CSV")
	fmt.Println("Records written = ", numEtherumRecordsWritten)

	// upload back to s3
	s3Utils.UploadToS3(s3Bucket, bitcoinFileName)
	s3Utils.UploadToS3(s3Bucket, etherumFileName)
}



func main() {

	client := rest.New(auth.New(os.Getenv("FTX_KEY"), os.Getenv("FTX_SECRET")))

	// pull new data
	currentBitcoinRecords, err := client.Candles(&markets.RequestForCandles{
		ProductCode: "BTC/USD",
		Resolution:  86400, //day
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Pulled records for Bitcoin", currentBitcoinRecords)
	currentEthereumRecords, err := client.Candles(&markets.RequestForCandles{
		ProductCode: "ETH/USD",
		Resolution:  86400, //day
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Pulled records for Etherum", currentEthereumRecords)


	// Call the Python Program here


}
