package main

import (
	"fmt"
	"log"
	"os"

	dataframe "github.com/go-gota/gota/dataframe"
	"github.com/go-numb/go-ftx/auth"
	"github.com/go-numb/go-ftx/rest"

	// "github.com/go-numb/go-ftx/rest/private/orders"
	// "github.com/go-numb/go-ftx/rest/private/account"
	// "github.com/go-numb/go-ftx/rest/public/futures"
	"github.com/go-numb/go-ftx/rest/public/markets"
	// "github.com/go-numb/go-ftx/types"
)

func readCsvFileIntoDF(filePath string) dataframe.DataFrame {
	f, err := os.Open(filePath)
	if err != nil {
		log.Fatal("Unable to read input file "+filePath, err)
	}
	defer f.Close()
	df := dataframe.ReadCSV(f)

	// csvReader := csv.NewReader(f)
	// records, err := csvReader.ReadAll()
	if err != nil {
		log.Fatal("Unable to parse file as CSV for "+filePath, err)
	}

	return df
}

func main() {

	client := rest.New(auth.New(os.Getenv("FTX_KEY"), os.Getenv("FTX_SECRET")))

	res, err := client.Candles(&markets.RequestForCandles{
		ProductCode: "BTC/USD",
		Resolution:  86400,
		Limit:       2, // optional
		// Start:       time.Now().Add(-2500 * time.Second).Unix(), // optional
		// End:         time.Now().Unix(),                          // optional
	})
	fmt.Println(res)

	if err != nil {
		log.Fatal(err)
	}

	// client.Requ

	// book, err := client.GetBook("BTC-USD", 1)
	// if err != nil {
	// 	println(err.Error())
	// }
	// fmt.Println("book = ", book)

	// lastPrice, err := decimal.NewFromString(book.Bids[0].Price)
	// if err != nil {
	// 	println(err.Error())
	// }
	// fmt.Println(lastPrice, "last price")
	// fmt.Printf("Last price %v", lastPrice)

	// try pulling historical candles. This works
	//  [ time, low, high, open, close, volume ]
	// historic_rates, err := client.GetHistoricRates("BTC-USD", coinbasepro.GetHistoricRatesParams{Granularity: 86400})
	// if err != nil {
	// 	println(err.Error())
	// }

	// // loop through the historic candles
	// for idx, entry := range historic_rates {
	// 	fmt.Println(idx, entry)
	// 	log.Output(1, fmt.Sprint(idx))
	// }
	// fmt.Println("New")
	// open csv file, add new candles to the .csv
	bitcoin_df := readCsvFileIntoDF("./data/historic_crypto_prices - bitcoin_jan_2017_sep_4_2021.csv")

	fmt.Println(bitcoin_df)

}
