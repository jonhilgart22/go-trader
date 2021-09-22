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
	"github.com/jonhilgart22/go-trader/tree/master/go_app/csvUtils"
)

type historicCandles struct {
	Date   time.Time `csv:"date"`
	Open   float64   `csv:"open"`
	High   float64   `csv:"high"`
	Low    float64   `csv:"low"`
	Close  float64   `csv:"close"`
	Volume float64   `csv:"volume"`
}

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

func FindNewestCsvDate(inputRecords []historicCandles) time.Time {
	var newestDate time.Time
	for _, historicVal := range inputRecords {
		if historicVal.Date.After(newestDate) {
			newestDate = historicVal.Date
		}
	}
	return newestDate
}

func writeNewCsvData(currentRecords *markets.ResponseForCandles, newestDate time.Time, csvFileName string) int {
	loc, _ := time.LoadLocation("UTC")
	today := time.Now().In(loc)
	roundedToday := csvUtils.RoundTimeToDay(today)

	numRecordsWritten := 0
	for _, currentVal := range *currentRecords {

		if currentVal.StartTime.After(newestDate) && !currentVal.StartTime.Equal(roundedToday) { // add this data, but not today's data

			f, err := os.OpenFile(csvFileName, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
			if err != nil {
				fmt.Println(err)
				return 0
			}
			w := csv.NewWriter(f)
			// csv format is date,open,high,low,close,volume
			// need to convert all to strings
			w.Write([]string{
				fmt.Sprintf("%d-%02d-%02d",
					currentVal.StartTime.Year(),
					currentVal.StartTime.Month(),
					currentVal.StartTime.Day()),
				fmt.Sprintf("%f", currentVal.Open),
				fmt.Sprintf("%f", currentVal.High),
				fmt.Sprintf("%f", currentVal.Low),
				fmt.Sprintf("%f", currentVal.Close),
				fmt.Sprintf("%f", currentVal.Volume)})
			w.Flush()
			numRecordsWritten += 1
		}
	}
	return numRecordsWritten
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

	// open csv file, add new candles to the .csv
	const bitcoinFileName string = "./data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021 copy.csv"
	const etherumFileName string = "./data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv"
	const s3Bucket string = "go-trader"
	const s3EtherumItem string = "data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv"
	const s3BitcoinItem string = "data/historic_crypto_prices - etherum_jan_2017_sept_4_2021 copy.csv"

	// download the files from s3
	DownloadFromS3(s3Bucket, s3EtherumItem)
	DownloadFromS3(s3Bucket, s3BitcoinItem)

	// read the data into memory
	bitcoinRecords := readCsvFile(bitcoinFileName)
	etherumRecords := readCsvFile(etherumFileName)

	newestBitcoinDate := FindNewestCsvDate(bitcoinRecords)
	newestEtherumDate := FindNewestCsvDate(etherumRecords)

	fmt.Println(newestBitcoinDate, "newestBitcoinDate")
	fmt.Println(newestEtherumDate, "newestEtherumDate")

	// add new data as needed
	// numBitcoinRecordsWritten := writeNewCsvData(currentBitcoinRecords, newestBitcoinDate, bitcoinFileName)
	// fmt.Println("Finished Bitcoin CSV")
	// fmt.Println("Records written = ", numBitcoinRecordsWritten)
	// numEtherumRecordsWritten := writeNewCsvData(currentEthereumRecords, newestEtherumDate, etherumFileName)
	// fmt.Println("Finished Etherum CSV")
	// fmt.Println("Records written = ", numEtherumRecordsWritten)

}
