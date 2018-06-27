package cron

import (
    "log"
    "fmt"
    "context"
    "encoding/json"
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/ethclient"
    "github.com/ninjadotorg/handshake-cryptosign/event/config"
    "github.com/ninjadotorg/handshake-cryptosign/event/utils"
)

var scanRunning = false

func ScanTx() {
    if scanRunning {
        fmt.Println("Scan job is running.")
        return;
    }
    scanRunning = true
    // todo get list transaction pending 
    transactions, err := txDAO.GetAllPending()
    if err != nil {
        log.Println("Scan Tx error", err.Error())
        return; 
    }
    if len(transactions) == 0 {
        log.Println("Scan Tx: don't have any pending tx")
        return;
    }

    log.Printf("Have %d pending tx\n", len(transactions))

    conf := config.GetConfig()
    networkUrl := conf.GetString("blockchainNetwork")

    etherClient, err := ethclient.Dial(networkUrl)
    if err != nil {
        log.Printf("Scan Tx: connect to network %s fail!\n", networkUrl)
        return;
    }

    // todo loop & parse transaction
    for _, transaction := range transactions {
        log.Printf("start scan %s\n", transaction.Hash)
        txHash := common.HexToHash(transaction.Hash)
        tx, pending, err := etherClient.TransactionByHash(context.Background(), txHash)
        if err == nil && !pending {
            log.Printf("Tx %s is not pending, start check success or fail\n", transaction.Hash)
            receipt, err := etherClient.TransactionReceipt(context.Background(), txHash)
            if err != nil {
                log.Println("Scan Tx: get receipt error", err.Error())
                continue;
            }
            log.Printf("Tx %s has receipt, status %d\n", transaction.Hash, receipt.Status)
            if receipt.Status == 0 {
                // case fail
                _, methodJson := utils.DecodeTransactionInput("PredictionHandshake", common.ToHex(tx.Data()))
                // call REST fail
                var jsonData map[string]interface{}
                json.Unmarshal([]byte(methodJson), &jsonData)
                jsonData["status"] = 0
                log.Println("hook fail", jsonData)
                err := hookService.Event(jsonData)
                if err != nil {
                    log.Println("Hook event fail error: ", err.Error())
                    log.Println(methodJson)
                }
            } else if receipt.Status == 1 {
                // case success
                log.Printf("Tx %s has receipt, logs %d\n", transaction.Hash, len(receipt.Logs))
                if len(receipt.Logs) > 0 {
                    for _, l := range receipt.Logs {
                        _, eventJson := utils.DecodeTransactionLog("PredictionHandshake", l)
                        var jsonData map[string]interface{}
                        json.Unmarshal([]byte(eventJson), &jsonData)
                        jsonData["status"] = 1
                        // call REST API SUCCESS with event
                        log.Println("hook success", jsonData)
                        err := hookService.Event(jsonData)
                        if err != nil {
                            log.Println("Hook event failed: ", err.Error())
                            log.Println(eventJson)
                        }
                    }
                }
            } else {
                log.Println("Unknown case", tx.Hash)
            }
        } else {
            log.Printf("Tx %s is pending or error occured\n", transaction.Hash, err.Error())
        }
    }
    scanRunning = false
}