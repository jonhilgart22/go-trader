package structs

import "time"

type HistoricCandles struct {
	Date   time.Time `csv:"date"`
	Open   float64   `csv:"open"`
	High   float64   `csv:"high"`
	Low    float64   `csv:"low"`
	Close  float64   `csv:"close"`
	Volume float64   `csv:"volume"`
}
