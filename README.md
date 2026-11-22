# FeeOrbit Fee Ledger

Reconcile crypto trading fees and posted cashback from two CSV files. The tool runs locally with Python 3.9 or later, using only the standard library.

Maintained by FeeOrbit. [Official FeeOrbit website](https://www.feeorbit.com/) · [FeeOrbit reconciliation guide](https://www.feeorbit.com/guides/actual-trading-fee-after-cashback)

```sh
python3 fee_ledger.py --fills examples/fills.csv --cashback examples/cashback.csv
```

```text
Period: 'example-order'
  Executed volume: 1000.00 USDT
  Trading fees:    1.00 USDT
  Posted cashback: 0.25 USDT
  Pending credits: 0 USDT
  Net trading fee: 0.75 USDT
  Effective fee:   0.075%
```

The included figures are illustrative. The program reads two local files and prints the result. It makes no network requests and requires no login or API key.

## Bring your own statement

Use one account and one exchange per run. Keep real statement files outside the repository. The tool accepts the UTF-8 CSV format published here. Map your exchange's export into it before running the command.

| File | Required columns |
| --- | --- |
| Fills | `fill_id,period_id,quote_asset,executed_value,fee_asset,fee` |
| Cashback | `credit_id,period_id,asset,amount,status` |

- Use one row per executed fill and a unique `fill_id`. If the exchange reuses identifiers between symbols, prefix them with the symbol. `executed_value` is the trade value in the quote asset. Include both entry and exit fills when measuring a round trip.
- Use one row per cashback credit and a unique `credit_id`. Enter positive credit amounts with status `posted` or `pending`. Use a header-only cashback file when there are no credits. Leave out canceled or reversed credits.
- Give a credit and the fills it covers the same `period_id`. If the credit covers several trades without a fill-by-fill breakdown, group all covered fills by the actual settlement period. Include each fill and credit once.
- v0.1 requires all values to use one asset, such as USDT. Convert cross-asset entries before importing and keep the original amounts and conversion records with your statement. [FeeOrbit's reconciliation guide](https://www.feeorbit.com/guides/actual-trading-fee-after-cashback) explains the mapping and valuation.
- Use recorded fill fees after any discount already applied by the exchange. Leave inviter income paid to another account, funding, withdrawals and trading P&L outside the inputs.

The tool subtracts posted cashback from charged fees and divides the result by executed volume to calculate the effective rate. Pending credits appear separately. The percentage is rounded to eight decimal places. For an estimate before you trade, use the [FeeOrbit Fee Comparison Calculator](https://www.feeorbit.com/tools/fee-comparison).

### Mapping a Binance Spot statement

Export completed fills from [Binance Spot Trade History](https://www.binance.com/en-GB/support/faq/how-to-calculate-binance-spot-trading-fees-e85d6e703b874674840122196b89780a). In Binance’s [spot account trade records](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/account#account-trade-list), the executed quote value corresponds to `quoteQty`, and the commission amount and asset correspond to `commission` and `commissionAsset`. Use the completed credit from your rewards statement as a separate row. Copy the column headers from this repository’s examples when preparing the two input files.

## Verify the example

```sh
python3 -m unittest discover -s tests
```

Released under the [MIT License](LICENSE) by FeeOrbit.
