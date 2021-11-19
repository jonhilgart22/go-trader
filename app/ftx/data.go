package ftx

import (
	"log"
	"strings"
	"time"

	"github.com/grishinsana/goftx"
	"github.com/grishinsana/goftx/models"
	"github.com/shopspring/decimal"
)

func ptrInt(i int) *int {
	return &i
}

func SellOrder(ftxClient *goftx.Client, marketToOrder string) {
	accountBalance, err := ftxClient.Wallet.GetBalances()
	log.Println(marketToOrder, "marketToOrder")

	if err != nil {
		panic(err)
	}
	var coinFree decimal.Decimal
	// figure out how much BTC we have
	for _, balance := range accountBalance {
		log.Println(balance.Coin, "balance.Coin")
		splitMarketStrings := strings.Split(marketToOrder, "/")
		// index 0 is the base currency, index 1 is the quote currency
		if balance.Coin == splitMarketStrings[0] {
			coinFree = balance.Total
		}
	}
	log.Printf("Remaining coin %v for market %v", coinFree, marketToOrder)
	sellOrder, err := ftxClient.PlaceOrder(&models.PlaceOrderPayload{
		Market: marketToOrder,
		Side:   "sell",
		Size:   coinFree,
		Type:   "market"})
	if err != nil {
		panic(err)
	}
	log.Printf("Sell order = %v", sellOrder)
}

func PurchaseOrder(client *goftx.Client, size decimal.Decimal, marketName string) {

	order, err := client.PlaceOrder(&models.PlaceOrderPayload{
		Market: marketName,
		Side:   "buy",
		Size:   size,
		Type:   "market",
	})
	if err != nil {
		panic(err)
	}
	log.Println(order, "Order")

	// STOP LOSS ORDER

	// trailValue := newestClosePrice.Mul(stopLossPct).Mul(decimal.NewFromFloat32(-1.0))
	// log.Println(trailValue, "Trail Value")

	// stop loss should be handled by Python
	// triggerOrder, err := client.PlaceTriggerOrder(&models.PlaceTriggerOrderPayload{
	// 	Market:     marketName,
	// 	Side:       "sell",
	// 	Size:       size,
	// 	Type:       "trailingStop",
	// 	TrailValue: &trailValue,
	// })
	// if err != nil {
	// 	panic(err)
	// }
	// log.Println("Trigger Order", triggerOrder)
}

func NewClient(key string, secret string, subaccountName string) *goftx.Client {
	client := goftx.New(goftx.WithAuth(
		key,
		secret,
		subaccountName),
		goftx.WithFTXUS())
	return client
}

func PullDataFromFtx(client *goftx.Client, productCode string, resolution int) []*models.HistoricalPrice {

	records, err := client.Markets.GetHistoricalPrices(productCode,
		&models.GetHistoricalPricesParams{
			Resolution: models.Day,
			StartTime:  ptrInt(int(time.Now().Add(-14 * 86400 * time.Second).Unix())), // last 14 days
			EndTime:    ptrInt(int(time.Now().Unix())),
		})

	if err != nil {
		log.Fatal(err)
	}
	log.Println("Pulled records for", productCode)
	log.Println("Records =", records)
	return records
}
