package alphaVantage

import (
	"fmt"
	"log"
	"os"
	"time"

	"github.com/ClintonMorrison/goAlphaVantage/pkg/alphaVantage"
	"github.com/grishinsana/goftx/models"
	"github.com/shopspring/decimal"
)

func PullDataFromAlphaVantage(productCode string) []*models.HistoricalPrice {
	log.Println("Pulling Alpha Vantage Data")
	client := alphaVantage.Client().
		Key(os.Getenv("ALPHA_VANTAGE_KEY"))
	quotes, err := client.TimeSeriesDaily("TBT", alphaVantage.SIZE_COMPACT)
	if err != nil {
		fmt.Println(err)
	}

	for _, quote := range quotes.Sorted() {
		fmt.Printf("%s: %f %f %f %f %f\n", quote.Time.Format("2006-01-02"), quote.Open, quote.High, quote.Low, quote.Close, quote.Volume)
	}

	var records []*models.HistoricalPrice

	newestDate := time.Date(2017, time.Month(1), 7, 0, 0, 0, 0, time.UTC)
	// // check if the newest date we have is not today's date (UTC). If so, we're on a weekend or holiday when markets are closed
	// // need to take the last row and propagate it forward to today

	for _, quote := range quotes.Sorted() {
		open := decimal.NewFromFloat(quote.Open)
		high := decimal.NewFromFloat(quote.High)
		low := decimal.NewFromFloat(quote.Low)
		close := decimal.NewFromFloat(quote.Close)
		volume := decimal.NewFromFloat(quote.Volume)

		date, err := time.Parse("2006-01-2", quote.Time.Format("2006-01-02"))
		if err != nil {
			fmt.Println(err)
		}

		if date.After(newestDate) {
			newestDate = date
		}

		records = append(records, &models.HistoricalPrice{
			StartTime: date,
			Open:      open,
			High:      high,
			Low:       low,
			Close:     close,
			Volume:    volume,
		})
	}
	log.Println(newestDate, "newestDate")

	// Defining duration
	d := (24 * time.Hour)
	loc, _ := time.LoadLocation("UTC")
	missingDaysDelta := time.Now().In(loc).Truncate(d).Sub(newestDate).Hours() / 24
	missingDaysDelta -= 1
	log.Println(missingDaysDelta, "missingDaysDelta")
	// subtract one to exclude the current date

	// for each day that we are missing , except for today, duplicate the last row via calls to the Yahoo API
	lastRecord := records[len(records)-1]

	for i := 0; i < int(missingDaysDelta); i++ {
		dateAdd := i + 1

		// create a copy of the last record
		newLastRecord := &models.HistoricalPrice{
			StartTime: lastRecord.StartTime,
			Open:      lastRecord.Open,
			High:      lastRecord.High,
			Low:       lastRecord.Low,
			Close:     lastRecord.Close,
			Volume:    lastRecord.Volume,
		}
		newLastRecord.StartTime = newestDate.Truncate(d).AddDate(0, 0, dateAdd)
		log.Println(newLastRecord, "newLastRecord")

		records = append(records, newLastRecord)
	}
	return records
}
