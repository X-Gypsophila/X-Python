#!/usr/bin/env python3
"""
离线记账工具（极简版）
- 无第三方依赖
- 本地 SQLite 持久化
- 命令行交互，适合离线环境
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

DB_PATH = Path("account_book.db")


@dataclass
class Record:
    amount: Decimal
    category: str
    note: str
    record_type: str  # income / expense
    created_at: str


class LedgerApp:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount TEXT NOT NULL,
                category TEXT NOT NULL,
                note TEXT NOT NULL,
                record_type TEXT NOT NULL CHECK (record_type IN ('income', 'expense')),
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def add_record(self, record: Record) -> None:
        self.conn.execute(
            """
            INSERT INTO records (amount, category, note, record_type, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(record.amount),
                record.category.strip(),
                record.note.strip(),
                record.record_type,
                record.created_at,
            ),
        )
        self.conn.commit()

    def list_recent(self, limit: int = 10) -> list[sqlite3.Row]:
        rows = self.conn.execute(
            """
            SELECT id, amount, category, note, record_type, created_at
            FROM records
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return rows

    def summary(self) -> dict[str, Decimal]:
        result = {"income": Decimal("0"), "expense": Decimal("0")}
        rows = self.conn.execute(
            "SELECT amount, record_type FROM records"
        ).fetchall()
        for row in rows:
            amt = Decimal(row["amount"])
            result[row["record_type"]] += amt
        result["balance"] = result["income"] - result["expense"]
        return result

    def close(self) -> None:
        self.conn.close()


def parse_amount(value: str) -> Decimal:
    try:
        amt = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("金额格式不正确") from exc
    if amt <= 0:
        raise ValueError("金额必须大于 0")
    return amt.quantize(Decimal("0.01"))


def ask_record_type() -> str:
    while True:
        v = input("类型 [1=支出, 2=收入]: ").strip()
        if v == "1":
            return "expense"
        if v == "2":
            return "income"
        print("请输入 1 或 2")


def ask_non_empty(prompt: str, default: str = "未分类") -> str:
    v = input(prompt).strip()
    return v or default


def print_summary(app: LedgerApp) -> None:
    s = app.summary()
    print("\n=== 总览 ===")
    print(f"总收入: {s['income']}")
    print(f"总支出: {s['expense']}")
    print(f"结余  : {s['balance']}")


def print_recent(app: LedgerApp) -> None:
    rows = app.list_recent(10)
    print("\n=== 最近 10 条 ===")
    if not rows:
        print("暂无记录")
        return
    for row in rows:
        sign = "+" if row["record_type"] == "income" else "-"
        print(
            f"#{row['id']:03d} {row['created_at']} {sign}{row['amount']} "
            f"[{row['category']}] {row['note']}"
        )


def add_flow(app: LedgerApp) -> None:
    print("\n--- 新增记录 ---")
    rtype = ask_record_type()

    while True:
        try:
            amount = parse_amount(input("金额: ").strip())
            break
        except ValueError as e:
            print(e)

    category = ask_non_empty("分类(可空): ", default="未分类")
    note = ask_non_empty("备注(可空): ", default="无")

    record = Record(
        amount=amount,
        category=category,
        note=note,
        record_type=rtype,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    app.add_record(record)
    print("已保存。")


def main() -> None:
    app = LedgerApp()
    print("离线记账工具已启动（数据文件: account_book.db）")

    try:
        while True:
            print("\n请选择操作:")
            print("1) 新增记账")
            print("2) 查看总览")
            print("3) 查看最近记录")
            print("0) 退出")

            choice = input("输入编号: ").strip()
            if choice == "1":
                add_flow(app)
            elif choice == "2":
                print_summary(app)
            elif choice == "3":
                print_recent(app)
            elif choice == "0":
                print("已退出，再见。")
                break
            else:
                print("无效输入，请重试。")
    finally:
        app.close()


if __name__ == "__main__":
    main()
