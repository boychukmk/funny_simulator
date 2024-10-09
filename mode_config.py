from abc import abstractmethod, ABC
from random import Random
import requests
from decimal import Decimal
from datetime import date, timedelta
from typing import Iterator
from dataclasses import dataclass
from itertools import count


@dataclass
class AssetPrice:
    BTC: Decimal
    ETH: Decimal
    BNB: Decimal
    SOL: Decimal
    MKR: Decimal
    XPR: Decimal
    ADA: Decimal


class AssetPriceHistory(ABC):
    """
    Історія цін активів.

    Може бути перевизначена в дочірніх класах для різних ситуацій.
    """

    @abstractmethod
    def __iter__(self) -> Iterator[tuple[date, AssetPrice]]:
        """
        Повертає історію цін активів у вигляді кортежів (дата, ціни активів).
        """
        ...


@dataclass
class RandomAssetPriceHistory(AssetPriceHistory):
    """
    Історія цін активів, де ціни змінюються випадковим чином на основі ціни за попередній день.
    """
    price_multiplier: tuple[float, float] = (0.5, 1.5)  # Множник ціни актива; ціна може змінюватися від -50% до +50%
    seed: int = 42

    def __post_init__(self):
        self.random = Random()
        self.random.seed(self.seed)

    def __iter__(self) -> Iterator[tuple[date, AssetPrice]]:
        today = date.today()
        base_asset_price = AssetPrice(
            BTC=Decimal('20000'),
            ETH=Decimal('1500'),
            BNB=Decimal('300'),
            SOL=Decimal('25'),
            MKR=Decimal('1200'),
            XPR=Decimal('0.5'),
            ADA=Decimal('0.5')
        )

        # Початкові ціни для першого дня
        previous_asset_price = base_asset_price

        for day in count():
            date_ = today + timedelta(days=day)

            if day == 0:
                # Для першого дня використовуємо базові ціни
                asset_price = previous_asset_price
            else:
                # Генеруємо нові ціни на основі цін за попередній день
                asset_price = AssetPrice(**{
                    field: getattr(previous_asset_price, field) * Decimal(self.random.uniform(*self.price_multiplier))
                    for field in AssetPrice.__dataclass_fields__.keys()
                })

            # Зберігаємо нові ціни як попередні для наступного дня
            previous_asset_price = asset_price

            yield date_, asset_price


@dataclass
class RealAssetPriceHistory(AssetPriceHistory):
    """
    Реальна історія цін активів, отримана через API Binance.
    """
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'MKRUSDT', 'XRPUSDT', 'ADAUSDT']

    def __iter__(self) -> Iterator[tuple[date, AssetPrice]]:
        for _ in range(30):  # Симулюємо 30 "днів"
            # Отримуємо дані з Binance API
            prices = self.get_crypto_prices(self.symbols)

            # Формуємо запис для поточного дня
            current_date = date.today()
            yield (
                current_date,
                AssetPrice(
                    BTC=Decimal(prices['BTCUSDT']),
                    ETH=Decimal(prices['ETHUSDT']),
                    BNB=Decimal(prices['BNBUSDT']),
                    SOL=Decimal(prices['SOLUSDT']),
                    MKR=Decimal(prices['MKRUSDT']),
                    XPR=Decimal(prices['XRPUSDT']),
                    ADA=Decimal(prices['ADAUSDT'])
                )
            )

    @staticmethod
    def get_crypto_prices(symbols):
        url = "https://api.binance.com/api/v3/ticker/price"
        prices = {}

        for symbol in symbols:
            params = {'symbol': symbol}
            response = requests.get(url, params=params)
            data = response.json()
            prices[symbol] = Decimal(data['price'])

        return prices


if __name__ == '__main__':
    from itertools import islice, count
    import argparse

    parser = argparse.ArgumentParser(description="Симулятор історії цін активів.")
    parser.add_argument(
        '--mode',
        choices=['real', 'random'],
        default='real',
        help='Виберіть режим: "real" для реальних цін або "random" для випадкових.'
    )
    args = parser.parse_args()

    if args.mode == 'real':
        history = RealAssetPriceHistory()
    else:
        history = RandomAssetPriceHistory()

    print('-' * 10, history.__class__.__name__, '-' * 10)
    for date_, asset_price in islice(history, 10):
        print(date_, asset_price)
