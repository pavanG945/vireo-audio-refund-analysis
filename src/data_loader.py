"""Load the five client-supplied CSVs. No cleaning happens here."""
import pandas as pd

from . import config


def load_tickets() -> pd.DataFrame:
    df = pd.read_csv(config.TICKETS_CSV)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["first_response_at"] = pd.to_datetime(df["first_response_at"])
    df["resolved_at"] = pd.to_datetime(df["resolved_at"])
    return df


def load_orders() -> pd.DataFrame:
    df = pd.read_csv(config.ORDERS_CSV)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def load_customers() -> pd.DataFrame:
    return pd.read_csv(config.CUSTOMERS_CSV)


def load_products() -> pd.DataFrame:
    return pd.read_csv(config.PRODUCTS_CSV)


def load_agents() -> pd.DataFrame:
    df = pd.read_csv(config.AGENTS_CSV)
    return df


def load_all():
    return {
        "tickets": load_tickets(),
        "orders": load_orders(),
        "customers": load_customers(),
        "products": load_products(),
        "agents": load_agents(),
    }
