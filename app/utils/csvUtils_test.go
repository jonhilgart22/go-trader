package utils

import (
	"encoding/csv"
	"fmt"
	"io/ioutil"
	"os"
	"syscall"
	"testing"
	"time"

	"github.com/grishinsana/goftx/models"
	"github.com/jonhilgart22/go-trader/app/structs"
	"github.com/shopspring/decimal"
)


func TestFindNewestData(t *testing.T) {
	fmt.Println("TestFindNewestData")
	historicalData := []structs.HistoricCandles{}

	dayOneOpen, err := decimal.NewFromString("900.0")
	if err != nil {
		panic(err)
	}
	dayOneHigh, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayOneClose, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayOneVolume, err := decimal.NewFromString("3000.0")
	if err != nil {
		panic(err)
	}
	dayTwoOpen, err := decimal.NewFromString("900.0")
	if err != nil {
		panic(err)
	}
	dayTwoHigh, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayTwoClose, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayTwoVolume, err := decimal.NewFromString("3000.0")
	if err != nil {
		panic(err)
	}
	dayThreeOpen, err := decimal.NewFromString("9300.0")
	if err != nil {
		panic(err)
	}
	dayThreeHigh, err := decimal.NewFromString("6300.0")
	if err != nil {
		panic(err)
	}
	dayThreeClose, err := decimal.NewFromString("30340.0")
	if err != nil {
		panic(err)
	}
	dayThreeVolume, err := decimal.NewFromString("304500.0")
	if err != nil {
		panic(err)
	}

	dayOne := structs.HistoricCandles{Date: time.Date(2020, time.Month(9), 1, 0, 0, 0, 0, time.UTC),
		Open:   dayOneOpen,
		High:   dayOneHigh,
		Close:  dayOneClose,
		Volume: dayOneVolume}
	historicalData = append(historicalData, dayOne)

	dayTwo := structs.HistoricCandles{Date: time.Date(2021, time.Month(10), 1, 0, 0, 0, 0, time.UTC),
		Open:   dayTwoOpen,
		High:   dayTwoHigh,
		Close:  dayTwoClose,
		Volume: dayTwoVolume}
	historicalData = append(historicalData, dayTwo)

	dayThree := structs.HistoricCandles{Date: time.Date(2020, time.Month(10), 1, 0, 0, 0, 0, time.UTC),
		Open:   dayThreeOpen,
		High:   dayThreeHigh,
		Close:  dayThreeClose,
		Volume: dayThreeVolume}
	historicalData = append(historicalData, dayThree)

	newestDate, NewestClosePrice := FindNewestData(historicalData)
	fmt.Println(newestDate, "newestDate")
	fmt.Println(NewestClosePrice, "NewestClosePrice")
	// see if newestcloseprice equals 300.0
	if NewestClosePrice.String() != "300" {
		t.Error("NewestClosePrice is not 300")
	}
	// see if date is 2020-10-01 00:00:00 +0000 UTC
	if newestDate.Before(time.Date(2020, time.Month(10), 1, 0, 0, 0, 0, time.UTC)) {
		t.Error("NewestDate is not 2020-10-01 00:00:00 +0000 UTC")
	}
}

func TestWriteNewCsvData(t *testing.T) {
	fmt.Println("TestWriteNewCsvData")
	historicalData := []*models.HistoricalPrice{}

	dayOneOpen, err := decimal.NewFromString("900.0")
	if err != nil {
		panic(err)
	}
	dayOneHigh, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayOneClose, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayOneVolume, err := decimal.NewFromString("3000.0")
	if err != nil {
		panic(err)
	}
	dayTwoOpen, err := decimal.NewFromString("900.0")
	if err != nil {
		panic(err)
	}
	dayTwoHigh, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayTwoClose, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayTwoVolume, err := decimal.NewFromString("3000.0")
	if err != nil {
		panic(err)
	}
	dayThreeOpen, err := decimal.NewFromString("9300.0")
	if err != nil {
		panic(err)
	}
	dayThreeHigh, err := decimal.NewFromString("6300.0")
	if err != nil {
		panic(err)
	}
	dayThreeClose, err := decimal.NewFromString("30340.0")
	if err != nil {
		panic(err)
	}
	dayThreeVolume, err := decimal.NewFromString("304500.0")
	if err != nil {
		panic(err)
	}

	dayOne := models.HistoricalPrice{StartTime: time.Date(2020, time.Month(9), 1, 0, 0, 0, 0, time.UTC),
		Open:   dayOneOpen,
		High:   dayOneHigh,
		Close:  dayOneClose,
		Volume: dayOneVolume}
	historicalData = append(historicalData, &dayOne)

	dayTwo := models.HistoricalPrice{StartTime: time.Date(2021, time.Month(10), 1, 0, 0, 0, 0, time.UTC),
		Open:   dayTwoOpen,
		High:   dayTwoHigh,
		Close:  dayTwoClose,
		Volume: dayTwoVolume}
	historicalData = append(historicalData, &dayTwo)

	loc, _ := time.LoadLocation("UTC")
	today := time.Now().In(loc)

	// we shouldn't include today's data
	dayThree := models.HistoricalPrice{StartTime: today,
		Open:   dayThreeOpen,
		High:   dayThreeHigh,
		Close:  dayThreeClose,
		Volume: dayThreeVolume}
	historicalData = append(historicalData, &dayThree)

	f, err := ioutil.TempFile("", "test_csv_writier")
	if err != nil {
		panic(err)
	}
	defer syscall.Unlink(f.Name())

	// write data to temp file
	newestDate := time.Date(2020, time.Month(10), 1, 0, 0, 0, 0, time.UTC)

	WriteNewCsvData(historicalData, newestDate, f.Name(), false)

	// check if the data was written to the file
	file, err := os.Open(f.Name())
	if err != nil {
		panic(err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		panic(err)
	}

	// check if the data was written to the file
	if len(records) != 2 {
		t.Error("The data was not written to the file. We may have included a third date")
	}

}
