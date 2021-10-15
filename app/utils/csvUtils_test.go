package utils

import (
    "fmt"
    "testing"
    "time"

    "github.com/jonhilgart22/go-trader/app/structs"
    "github.com/shopspring/decimal"
)

func TestFindNewestData(t *testing.T) {
    historicalData := make([]structs.HistoricCandles, 0, 3)
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

    historicalData[0] = structs.HistoricCandles{Date: time.Date(2020, time.Month(9), 1, 0, 0, 0, 0, time.UTC),
        Open:   dayOneOpen,
        High:   dayOneHigh,
        Close:  dayOneClose,
        Volume: dayOneVolume}

    historicalData[1] = structs.HistoricCandles{Date: time.Date(2021, time.Month(10), 1, 0, 0, 0, 0, time.UTC),
        Open:   dayTwoOpen,
        High:   dayTwoHigh,
        Close:  dayTwoClose,
        Volume: dayTwoVolume}

    historicalData[2] = structs.HistoricCandles{Date: time.Date(2020, time.Month(10), 1, 0, 0, 0, 0, time.UTC),
        Open:   dayThreeOpen,
        High:   dayThreeHigh,
        Close:  dayThreeClose,
        Volume: dayThreeVolume}
    newestDate, NewestClosePrice := FindNewestData(historicalData)
    fmt.Println(newestDate, "newestDate")
    fmt.Println(NewestClosePrice, "NewestClosePrice")
}
