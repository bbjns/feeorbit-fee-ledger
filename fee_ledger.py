"""Reconcile executed trading fees and posted cashback from local CSV files."""

import argparse
import csv
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
import re


FILL_COLUMNS = ("fill_id", "period_id", "quote_asset", "executed_value", "fee_asset", "fee")
CREDIT_COLUMNS = ("credit_id", "period_id", "asset", "amount", "status")
AMOUNT = re.compile(r"[0-9]{1,18}(?:\.[0-9]{1,18})?")
ASSET = re.compile(r"[A-Z0-9][A-Z0-9._-]{0,19}")
ZERO = Decimal(0)


@dataclass
class Totals:
    volume: Decimal = ZERO
    fees: Decimal = ZERO
    posted: Decimal = ZERO
    pending: Decimal = ZERO


def read_rows(path, columns):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        header = reader.fieldnames or []
        if len(header) != len(columns) or set(header) != set(columns):
            raise ValueError(f"{path}: expected CSV columns {', '.join(columns)}")
        identifiers = set()
        for row in reader:
            where = f"{path}:{reader.line_num}"
            if None in row or any(value is None or not value.strip() for value in row.values()):
                raise ValueError(f"{where}: expected a value for every CSV column")
            row = {key: value.strip() for key, value in row.items()}
            identifier = row[columns[0]]
            if identifier in identifiers:
                raise ValueError(f"{where}: duplicate {columns[0]} {identifier!r}")
            identifiers.add(identifier)
            yield where, row


def parse_amount(row, key, where):
    value = row[key]
    if not AMOUNT.fullmatch(value):
        raise ValueError(f"{where}: {key} must be a non-negative decimal with up to 18 digits on each side of the decimal point")
    return Decimal(value)


def reconcile(fills, credits):
    periods = {}
    asset = None
    for where, row in read_rows(fills, FILL_COLUMNS):
        if asset is None:
            asset = row["quote_asset"]
        if not ASSET.fullmatch(asset):
            raise ValueError(f"{where}: use an uppercase asset code, such as USDT")
        if row["quote_asset"] != asset or row["fee_asset"] != asset:
            raise ValueError(f"{where}: all executed values, fees and credits must be expressed in {asset}")
        volume = parse_amount(row, "executed_value", where)
        if volume == ZERO:
            raise ValueError(f"{where}: executed_value must be greater than zero")
        period = periods.setdefault(row["period_id"], Totals())
        period.volume += volume
        period.fees += parse_amount(row, "fee", where)

    if not periods:
        raise ValueError(f"{fills}: no fills to reconcile")

    for where, row in read_rows(credits, CREDIT_COLUMNS):
        if row["asset"] != asset:
            raise ValueError(f"{where}: credit asset must be {asset}")
        if row["period_id"] not in periods:
            raise ValueError(f"{where}: period {row['period_id']!r} has no matching fills")
        credit = parse_amount(row, "amount", where)
        period = periods[row["period_id"]]
        if row["status"] == "posted":
            period.posted += credit
        elif row["status"] == "pending":
            period.pending += credit
        else:
            raise ValueError(f"{where}: status must be posted or pending")

    return asset, periods


def print_report(asset, periods):
    for period_id, totals in periods.items():
        net = totals.fees - totals.posted
        rate = (net * 100 / totals.volume).quantize(Decimal("0.00000001"))
        formatted_rate = format(rate, "f").rstrip("0").rstrip(".")
        if rate == ZERO:
            formatted_rate = "0"
        print(f"Period: {period_id!r}")
        print(f"  Executed volume: {totals.volume:f} {asset}")
        print(f"  Trading fees:    {totals.fees:f} {asset}")
        print(f"  Posted cashback: {totals.posted:f} {asset}")
        print(f"  Pending credits: {totals.pending:f} {asset}")
        print(f"  Net trading fee: {net:f} {asset}")
        print(f"  Effective fee:   {formatted_rate}%")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fills", type=Path, required=True, help="fill CSV in FeeOrbit's ledger format")
    parser.add_argument("--cashback", type=Path, required=True, help="credit CSV in FeeOrbit's ledger format")
    args = parser.parse_args()
    try:
        with localcontext() as context:
            context.prec = 60
            context.rounding = ROUND_HALF_EVEN
            asset, periods = reconcile(args.fills, args.cashback)
            print_report(asset, periods)
    except (OSError, csv.Error, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
