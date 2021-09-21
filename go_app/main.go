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
	// "github.com/go-numb/go-ftx/types"
	// "github.com/go-gota/gota/dataframe"
	// "github.com/gocarina/gocsv"
)

// type DateTime struct {
// 	time.Time
// }

// // Convert the CSV string as internal date
// func (date *DateTime) UnmarshalCSV(csv string) (err error) {
// 	date.Time, err = time.Parse("2006-01-02", csv)
// 	return err
// }

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
		} else if Contains(line, "date") && Contains(line, "open") && Contains(line, "close") {
			continue
		}
		records = append(records, historicCandles{
			Date:  ParseDate(line[0]),
			Open:  ConvertStringToFloat(line[1]),
			High:  ConvertStringToFloat(line[2]),
			Low:   ConvertStringToFloat(line[3]),
			Close: ConvertStringToFloat(line[4]),
		})
	}

	return records
}

func main() {

	client := rest.New(auth.New(os.Getenv("FTX_KEY"), os.Getenv("FTX_SECRET")))

	// pull new data
	currentRecords, err := client.Candles(&markets.RequestForCandles{
		ProductCode: "BTC/USD",
		Resolution:  86400, //day
	})

	fmt.Println("res", currentRecords, "-------")

	if err != nil {
		log.Fatal(err)
	}

	// open csv file, add new candles to the .csv
	const bitcoinFileName string = "./data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021.csv"
	bitcoinRecords := readCsvFile(bitcoinFileName)

	// for _, newVal := range *res {
	var newestDate time.Time

	for _, historicVal := range bitcoinRecords {
		if historicVal.Date.After(newestDate) {
			newestDate = historicVal.Date
		}
	}
	fmt.Println(newestDate, "newestDate")

	for _, currentVal := range *currentRecords {
		if currentVal.StartTime.After(newestDate) {
			// this is new data we've pulled in
			fmt.Println(currentVal.StartTime, "start time current records")

			f, err := os.OpenFile(bitcoinFileName, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
			if err != nil {
				fmt.Println(err)
				return
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
		}
	}

	// fmt.Println(bitcoinRecords)

}
