package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"strconv"
	"time"

	"path/filepath"

	"github.com/go-numb/go-ftx/auth"
	"github.com/go-numb/go-ftx/rest"

	// "github.com/go-numb/go-ftx/rest/private/orders"
	// "github.com/go-numb/go-ftx/rest/private/account"
	// "github.com/go-numb/go-ftx/rest/public/futures"
	"github.com/go-numb/go-ftx/rest/public/markets"
	"github.com/jonhilgart22/go-trader/app/csvUtils"
	"github.com/jonhilgart22/go-trader/app/s3Utils"
	"github.com/jonhilgart22/go-trader/app/structs"
	"gopkg.in/yaml.v3"
)

func readCsvFile(filePath string) []structs.HistoricCandles {
	f, err := os.Open(filePath)
	if err != nil {
		panic(err)
	}
	reader := csv.NewReader(bufio.NewReader(f))
	defer f.Close()

	records := []structs.HistoricCandles{}

	for {
		line, error := reader.Read()
		if error == io.EOF {
			break
		} else if error != nil {
			panic(error)
		} else if csvUtils.Contains(line, "date") && csvUtils.Contains(line, "open") && csvUtils.Contains(line, "close") {
			continue
		}
		records = append(records, structs.HistoricCandles{
			Date:  csvUtils.ParseDate(line[0]),
			Open:  csvUtils.ConvertStringToFloat(line[1]),
			High:  csvUtils.ConvertStringToFloat(line[2]),
			Low:   csvUtils.ConvertStringToFloat(line[3]),
			Close: csvUtils.ConvertStringToFloat(line[4]),
		})
	}

	return records
}

func readYamlFile(fileLocation string) map[string]string {
	fmt.Println(" ")
	yfile, err := ioutil.ReadFile(fileLocation)

	if err != nil {
		panic(err)
	}
	data := make(map[string]string)
	err2 := yaml.Unmarshal(yfile, &data)
	if err2 != nil {
		panic(err)
	}
	for k, v := range data {

		fmt.Printf("%s -> %s\n", k, v)

	}
	fmt.Println("Finished reading in yaml constants")
	fmt.Println(" ")

	return data
}

func downloadUpdateReuploadData(currentBitcoinRecords *markets.ResponseForCandles, currentEthereumRecords *markets.ResponseForCandles, constantsMap map[string]string) {

	// download the files from s3
	// TODO: mkdir for data?
	fmt.Println("Downloading ", constantsMap["etherum_csv_filename"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"])
	fmt.Println("Downloading ", constantsMap["bitcoin_csv_filename"])
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"])

	// read the data into memory
	bitcoinRecords := readCsvFile(constantsMap["bitcoin_csv_filename"])
	etherumRecords := readCsvFile(constantsMap["etherum_csv_filename"])

	newestBitcoinDate := csvUtils.FindNewestCsvDate(bitcoinRecords)
	newestEtherumDate := csvUtils.FindNewestCsvDate(etherumRecords)
	fmt.Println(newestBitcoinDate, "newestBitcoinDate")
	fmt.Println(newestEtherumDate, "newestEtherumDate")

	// add new data as needed
	numBitcoinRecordsWritten := csvUtils.WriteNewCsvData(currentBitcoinRecords, newestBitcoinDate, constantsMap["bitcoin_csv_filename"])
	fmt.Println("Finished Bitcoin CSV")
	fmt.Println("Records written = ", numBitcoinRecordsWritten)
	numEtherumRecordsWritten := csvUtils.WriteNewCsvData(currentEthereumRecords, newestEtherumDate, constantsMap["etherum_csv_filename"])
	fmt.Println("Finished Etherum CSV")
	fmt.Println("Records written = ", numEtherumRecordsWritten)

	// upload back to s3
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["bitcoin_csv_filename"])
	s3Utils.UploadToS3(constantsMap["s3_bucket"], constantsMap["etherum_csv_filename"])
}

func pullDataFromFtx(productCode string, resolution int) *markets.ResponseForCandles {
	client := rest.New(auth.New(os.Getenv("FTX_KEY"), os.Getenv("FTX_SECRET")))

	records, err := client.Candles(&markets.RequestForCandles{
		ProductCode: productCode,
		Resolution:  resolution,
		Start:       time.Now().Add(-7 * 86400 * time.Second).Unix(), // last 7 days
		End:         time.Now().Unix(),                               // optional
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Pulled records for", productCode)
	fmt.Println("Records =", *records)
	return records
}

func downloadModelFiles(constantsMap map[string]string) {
	tcnEthModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["tcn_modelname_eth"], constantsMap["tcn_filename_eth"])
	tcnBtcModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["tcn_modelname_btc"], constantsMap["tcn_filename_btc"])

	nbeatsBtcModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["nbeats_modelname_btc"], constantsMap["nbeats_filename_btc"])
	nbeatsEthModelFilePath := filepath.Join(constantsMap["ml_model_dir_prefix"], constantsMap["nbeats_modelname_eth"], constantsMap["nbeats_filename_eth"])

	fmt.Println("Downloading = ", tcnEthModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], tcnEthModelFilePath)
	fmt.Println("Downloading = ", tcnBtcModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], tcnBtcModelFilePath)
	fmt.Println("Downloading = ", nbeatsEthModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], nbeatsEthModelFilePath)
	fmt.Println("Downloading = ", nbeatsBtcModelFilePath)
	s3Utils.DownloadFromS3(constantsMap["s3_bucket"], nbeatsBtcModelFilePath)

}

func copyOutput(r io.Reader) {
	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		fmt.Println(scanner.Text())
	}
}

func runPythonMlProgram(constantsMap map[string]string) {
	pwd, err := os.Getwd()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	fmt.Println("Current working directory = ", pwd)

	cmd := exec.Command("python", filepath.Join(pwd, constantsMap["python_script_path"]))
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		panic(err)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		panic(err)
	}
	err = cmd.Start()
	if err != nil {
		panic(err)
	}

	go copyOutput(stdout)
	go copyOutput(stderr)
	cmd.Wait()

}

func main() {

	// Read in the constants from yaml
	constantsMap := readYamlFile("app/constants.yml")

	// pull new data from FTX with day candles
	granularity, e := strconv.Atoi(constantsMap["candle_granularity"])
	if e != nil {
		panic(e)
	}
	currentBitcoinRecords := pullDataFromFtx(constantsMap["btc_product_code"], granularity)
	currentEthereumRecords := pullDataFromFtx(constantsMap["eth_product_code"], granularity)

	// Add new data to CSV from FTX to s3. This will be used by our Python program
	downloadUpdateReuploadData(currentBitcoinRecords, currentEthereumRecords, constantsMap)

	// Download the model files to be used by the python program
	// models need to be downloaded to models/checkpoints/{model_name}/{filename}
	// TODO: uncomment
	// don't need to do this
	// downloadModelFiles(constantsMap)

	// Call the Python Program here. This is kinda jank
	fmt.Println("Calling our Python program")

	runPythonMlProgram(constantsMap)

	// upload the model files after training

	// upload any config changes that we need to maintain state

}
