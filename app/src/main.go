package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "os/exec"
    "strconv"

    "path/filepath"

    "github.com/aws/aws-lambda-go/lambda"
    "github.com/shopspring/decimal"

    "github.com/grishinsana/goftx"
    "github.com/grishinsana/goftx/models"
    "github.com/jonhilgart22/go-trader/app/awsUtils"
    "github.com/jonhilgart22/go-trader/app/ftx"
    "github.com/jonhilgart22/go-trader/app/structs"
    "github.com/jonhilgart22/go-trader/app/utils"
)

func downloadUpdateReuploadData(currentBitcoinRecords []*models.HistoricalPrice, currentEthereumRecords []*models.HistoricalPrice, constantsMap map[string]string, runningOnAws bool) (decimal.Decimal, decimal.Decimal) {

    // download the files from s3
    awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"], runningOnAws)
    awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"], runningOnAws)

    // read the data into memory
    bitcoinRecords := utils.ReadCsvFile(constantsMap["bitcoin_csv_filename"], runningOnAws)
    etherumRecords := utils.ReadCsvFile(constantsMap["etherum_csv_filename"], runningOnAws)
    // spyRecords := utils.ReadCsvFile(constantsMap["spy_csv_filename"])

    newestBitcoinDate, newestClosePriceBtc := utils.FindNewestData(bitcoinRecords)
    newestEtherumDate, newestClosePriceEth := utils.FindNewestData(etherumRecords)
    // newestSpyDate, newestClosePriceSpy := utils.FindNewestData(spyRecords)
    log.Println(newestBitcoinDate, "newestBitcoinDate")
    log.Println(newestEtherumDate, "newestEtherumDate")
    // log.Println(spyRecords, "spyRecords")

    // add new data as needed
    numBitcoinRecordsWritten := utils.WriteNewCsvData(currentBitcoinRecords, newestBitcoinDate, constantsMap["bitcoin_csv_filename"], runningOnAws)
    log.Println("Finished Bitcoin CSV")
    log.Println("Records written = ", numBitcoinRecordsWritten)
    numEtherumRecordsWritten := utils.WriteNewCsvData(currentEthereumRecords, newestEtherumDate, constantsMap["etherum_csv_filename"], runningOnAws)
    log.Println("Finished ETH CSV")
    log.Println("Records written = ", numEtherumRecordsWritten)
    // numSpyRecordsWritten := utils.WriteNewCsvData(currentSpyRecords, newestSpyDate, constantsMap["spy_csv_filename"])
    // log.Println("Finished SPY CSV")
    // log.Println("Records written = ", numSpyRecordsWritten)

    // upload back to s3
    awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"], runningOnAws)
    awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"], runningOnAws)
    // awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["spy_csv_filename"])

    return newestClosePriceEth, newestClosePriceBtc
    //newestClosePriceSpy
}

func runPythonMlProgram(constantsMap map[string]string, coinToPredict string) {
    pwd, err := os.Getwd()
    if err != nil {
        log.Println(err)
        os.Exit(1)
    }
    log.Println("Current working directory = ", pwd)

    cmd := exec.Command("python", filepath.Join(pwd, constantsMap["python_script_path"]), fmt.Sprintf("--coin_to_predict=%v", coinToPredict))
    stdout, err := cmd.StdoutPipe()
    if err != nil {
        panic(err)
    }
    stderr, err := cmd.StderrPipe()
    if err != nil {
        os.Exit(1)
        panic(err)

    }
    err = cmd.Start()
    if err != nil {
        os.Exit(1)
        panic(err)
    }

    go utils.CopyOutput(stdout)
    go utils.CopyOutput(stderr)
    cmd.Wait()
}

func main() {
    lambda.Start(HandleRequest)
}

func HandleRequest(ctx context.Context, req structs.CloudWatchEvent) (string, error) {

    var runningOnAws bool = awsUtils.RunningOnAws()
    var coinToPredict string = req.CoinToPredict
    log.Printf("Coin to predict = %v", coinToPredict)
    // set env vars
    awsUtils.SetSsmToEnvVars()

    // Download all the config files
    awsUtils.DownloadFromS3("go-trader", "app/constants.yml", runningOnAws)

    // Read in the constants from yaml
    constantsMap := utils.ReadYamlFile("app/constants.yml")

    // Download the rest of the config files
    awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["actions_to_take_filename"], runningOnAws)
    //ml_config.yml
    awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["ml_config_filename"], runningOnAws)
    //trading_state_config.yml
    awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["trading_state_config_filename"], runningOnAws)
    //won_and_lost_amount.yml
    awsUtils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["won_and_lost_amount_filename"], runningOnAws)

    // pull new data from FTX with day candles
    granularity, e := strconv.Atoi(constantsMap["candle_granularity"])
    if e != nil {
        panic(e)
    }

    var ftxClient *goftx.Client
    var marketToOrder string
    if coinToPredict == "btc" {
        ftxClient = ftx.NewClient(os.Getenv("BTC_FTX_KEY"), os.Getenv("BTC_FTX_SECRET"), os.Getenv("BTC_SUBACCOUNT_NAME"))

        marketToOrder = "BTC/USD"

    } else if coinToPredict == "eth" {
        ftxClient = ftx.NewClient(os.Getenv("ETH_FTX_KEY"), os.Getenv("ETH_FTX_SECRET"), os.Getenv("ETH_SUBACCOUNT_NAME"))

        marketToOrder = "BTC/USD"
    }

    currentBitcoinRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["btc_product_code"], granularity)
    currentEthereumRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["eth_product_code"], granularity)
    // currentSpyRecords := ftx.PullDataFromFtx(ftxClient, constantsMap["spy_product_code"], granularity)

    // Add new data to CSV from FTX to s3. This will be used by our Python program
    newestClosePriceEth, newestClosePriceBtc := downloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, constantsMap, runningOnAws)
    log.Println(newestClosePriceBtc, "newestClosePriceBtc")
    log.Println(newestClosePriceEth, "newestClosePriceEth")
    // "newestClosePriceSpy")
    // newestClosePriceEth, newestClosePriceBtc, newestClosePriceSpy := downloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, currentSpyRecords, constantsMap)
    // log.Println(newestClosePriceBtc, "newestClosePriceBtc")
    // log.Println(newestClosePriceEth, "newestClosePriceEth")
    // log.Println(newestClosePriceSpy, "newestClosePriceSpy")

    // Call the Python Program here. This is kinda jank
    _, runningLocally := os.LookupEnv(("ON_LOCAL"))
    if runningLocally {
        log.Printf("Running only golang code locally")
    } else if runningOnAws {
        log.Printf("Calling our Python program with coin = %v", coinToPredict)
        runPythonMlProgram(constantsMap, coinToPredict)
    }
    // Read in the constants  that have been updated from our python ML program. Determine what to do based
    log.Println("Determining actions to take")
    actionsToTakeConstants := utils.ReadNestedYamlFile(constantsMap["actions_to_take_filename"]) // read in nested yaml?
    log.Println(actionsToTakeConstants[coinToPredict]["action_to_take"])
    actionToTake := actionsToTakeConstants[coinToPredict]["action_to_take"]

    // account information

    log.Println("Logging into FTX to get account info")
    subAccount, _ := ftxClient.SubAccounts.GetSubaccountBalances("eth_trading")

    log.Println("Sub Account", subAccount)

    info, err := ftxClient.Account.GetAccountInformation()
    if err != nil {
        panic(err)
    }
    log.Println(info, "info")
    log.Println(info.TotalAccountValue, "TotalAccountValue")
    log.Println(info.TotalPositionSize, "Total position size ")
    log.Println(info.Positions, "Positions")

    // TODO: once FTX allows short leveraged tokens in the US, add this to the short action
    if !runningLocally {
        switch actionToTake {
        case "none":
            log.Printf("Action for coin %v to take = none", coinToPredict)
        case "none_to_none":
            log.Printf("Action for coin %v to take = none_to_none", coinToPredict)
        case "buy_to_none": // liquidate all positions
            log.Printf("Action for coin %v to take = buy_to_none", coinToPredict)
            ftx.SellOrder(ftxClient, marketToOrder)

        case "short_to_none":
            log.Printf("Action for coin %v to take = short_to_none", coinToPredict)
        case "none_to_buy":
            log.Printf("Action for coin %v to take = none_to_buy", coinToPredict)

            log.Println("------")

            // TODO: update this with correct sizing
            size, err := decimal.NewFromString("0.001")
            log.Println("Taking a position worth ~", size.Mul(newestClosePriceBtc))
            if err != nil {
                panic(err)
            }

            ftx.PurchaseOrder(ftxClient, size, marketToOrder)

        case "none_to_short":
            log.Printf("Action for coin %v to take = none_to_short", coinToPredict)
        case "buy_to_continue_buy":
            log.Printf("Action for coin %v to take = buy_to_continue_buy.  Leaving everything as is for now", coinToPredict)
        case "short_to_continue_short":
            log.Printf("Action for coin %v to take = short_to_continue_short. Leaving everything as is for now", coinToPredict)
        default:
            panic("We didn't hit a case statement for action to take")
        }
    } else {
        log.Println("Running locally, not taking positions")
    }

    // upload any config changes that we need to maintain state
    if !runningLocally {
        //actions_to_take.yml
        awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["actions_to_take_filename"], runningOnAws)
        //constants.yml
        awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["constants_filename"], runningOnAws)
        //ml_config.yml
        awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["ml_config_filename"], runningOnAws)
        //trading_state_config.yml
        awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["trading_state_config_filename"], runningOnAws)
        //won_and_lost_amount.yml
        awsUtils.UploadToS3(constantsMap["s3_bucket"], constantsMap["won_and_lost_amount_filename"], runningOnAws)
    } else {
        log.Println("Running locally, not upload config files")
    }

    // send email
    if !runningLocally {
        awsUtils.SendEmail(fmt.Sprintf("Successfully executed go-trader for coin = %v", coinToPredict), constantsMap["logs_filename"], runningOnAws)
    } else {
        log.Println("No emails, running locally")
    }
    // all done!
    return "Finished!", nil

}
