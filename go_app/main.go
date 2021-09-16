package main

import (
	"fmt"

	coinbasepro "github.com/preichenberger/go-coinbasepro/v2"
	"github.com/shopspring/decimal"
)

func main() {
	client := coinbasepro.NewClient() // creds stored as environment vars, COINBASE_PRO_PASSPHRASE, COINBASE_PRO_KEY, COINBASE_PRO_SECRET
	fmt.Println(client)

	book, err := client.GetBook("BTC-USD", 1)
	if err != nil {
		println(err.Error())
	}
	fmt.Println("book = ", book)

	lastPrice, err := decimal.NewFromString(book.Bids[0].Price)
	if err != nil {
		println(err.Error())
	}
	fmt.Println(lastPrice, "last price")
	fmt.Printf("Last price %v", lastPrice)

	// try pulling historical candles. This works
	historic_rates, err := client.GetHistoricRates("BTC-USD", coinbasepro.GetHistoricRatesParams{Granularity: 86400})
	if err != nil {
		println(err.Error())
	}
	fmt.Println(historic_rates)

}
