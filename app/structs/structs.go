package structs

import (
	"time"

	"github.com/shopspring/decimal"
)

type HistoricCandles struct {
	Date   time.Time       `csv:"date"`
	Open   decimal.Decimal `csv:"open"`
	High   decimal.Decimal `csv:"high"`
	Low    decimal.Decimal `csv:"low"`
	Close  decimal.Decimal `csv:"close"`
	Volume decimal.Decimal `csv:"volume"`
}
