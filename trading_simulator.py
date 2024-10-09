from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from textwrap import dedent
from time import sleep

from mode_config import AssetPriceHistory, RealAssetPriceHistory, RandomAssetPriceHistory


class NotEnoughCash(Exception):
    pass


class WrongAssetName(ValueError):
    pass


class NotEnoughAsset(Exception):
    pass


class StopGameException(Exception):
    pass


def input_int(prompt: str) -> int:
    """ Функція для безпечного введення чисел """
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Неправильне введення, спробуйте ще раз. Необхідно ввести число!")


@dataclass
class PortfolioSimulator:
    history: AssetPriceHistory = field(default_factory=RealAssetPriceHistory)
    cash: Decimal = Decimal(100_000)  # стартовий капітал
    assets: defaultdict = field(default_factory=lambda: defaultdict(int))  # скільки активів ми маємо (спочатку нічого)
    day_count: int = 0  # Лічильник днів

    def __post_init__(self):
        if self.cash < 0:
            raise NotEnoughCash("Початковий капітал не може бути від'ємним")

        self.days = iter(self.history)
        self.next_day()  # отримуємо перший день і ціни активів
        self.initial_value = self.value
        self.logo = (Path(__file__).parent / 'logo.txt').read_text(encoding='utf-8')

    def next_day(self):
        """ Завершити день та отримати ціни нового дня """
        self.current_date, self.current_prices = next(self.days)
        self.day_count += 1  # Збільшуємо кількість днів

    def buy(self, asset: str, amount: int):
        """ Купити актив """
        try:
            price = getattr(self.current_prices, asset)
        except AttributeError:
            raise WrongAssetName(f"Немає такого активу: {asset}")
        cost = price * amount

        if self.cash < cost:
            raise NotEnoughCash(f"Недостатньо грошей для покупки активу: потрібно {cost}, а є {self.cash}")

        self.cash -= cost
        self.assets[asset] += amount

    def sell(self, asset: str, amount: int):
        """ Продати актив """
        if asset not in self.assets:
            raise WrongAssetName(f"Немає такого активу: {asset}")

        if (current_quantity := self.assets[asset]) < amount:
            raise NotEnoughAsset(f"Недостатньо активу для продажу: потрібно {amount}, а є {current_quantity}")

        try:
            self.cash += getattr(self.current_prices, asset) * amount
        except AttributeError:
            raise WrongAssetName(f"Немає такого активу: {asset}")
        self.assets[asset] -= amount

    @property
    def asset_values(self) -> list[tuple[str, int, Decimal]]:
        """ Вартість активів """
        return [
            (asset, quantity, getattr(self.current_prices, asset) * quantity)
            for asset in self.current_prices.__dataclass_fields__.keys()
            if (quantity := self.assets[asset]) != 0  # не показуємо те, чого не маємо
        ]

    @property
    def value(self) -> Decimal:
        """ Вартість портфеля """
        return self.cash + sum(price for _, _, price in self.asset_values)

    @property
    def profit(self) -> Decimal:
        """ Прибуток """
        return self.value - self.initial_value

    def run(self):
        """ Інтерактивний режим """
        self.print_greeting()

        while True:
            self.print_summary()
            try:
                self.user_action()
            except StopGameException:
                break

        self.print_result()

    def print_greeting(self):
        print(self.logo)
        print('Ласкаво просимо до симулятора торгівлі активами!')
        print('Спробуйте не прогоріти в перший день :>')

    def print_summary(self):
        print('-' * 40)
        print(f"День {self.day_count}")

        print("Ваші активи:")
        if not any(quantity > 0 for _, quantity, _ in self.asset_values):
            print("\t(пусто)")
        else:
            for asset, quantity, total in self.asset_values:
                print('\t'.join([asset, f'{quantity}шт', f'{total:,.2f}$']))

        print(f"Ваші гроші: {self.cash:,.2f}$")
        print(f"Вартість портфеля: {self.value:,.2f}$")
        print(f"Прибуток: {self.profit:,.2f}$")

        print('\nЦіни активів на сьогодні:')
        for asset in self.current_prices.__dataclass_fields__.keys():
            price = getattr(self.current_prices, asset)
            print('\t'.join([asset, f'{price:,.2f}$']))

    def user_action(self):
        """ Вибір дії користувача """
        action = input(dedent("""\n
            Що ви хочете зробити?
            1. Купити актив
            2. Продати актив
            3. Завершити день
            4. Завершити програму
        """)).strip()

        match action:
            case "1":
                self.buy_action()
                sleep(1)

            case "2":
                self.sell_action()
                sleep(1)

            case "3":
                try:
                    self.next_day()
                except StopIteration:
                    raise StopGameException()

            case "4":
                raise StopGameException()

            case _:
                print("Неправильний вибір, спробуйте ще раз.")

    def buy_action(self):
        """ Дія покупки активу через вибір зі списку """
        assets_list = list(self.current_prices.__dataclass_fields__.keys())
        print("Доступні активи для покупки:")
        for idx, asset in enumerate(assets_list, 1):
            print(f"{idx}. {asset}")

        while True:
            try:
                # Вибір активу за номером
                asset_idx = input_int("Виберіть актив за номером: ")
                if 1 <= asset_idx <= len(assets_list):
                    asset = assets_list[asset_idx - 1]
                    price = getattr(self.current_prices, asset)

                    # Розраховуємо максимальну кількість активу, яку можна купити
                    max_amount = self.cash // price
                    if max_amount == 0:
                        print(f"Недостатньо грошей для покупки {asset}. Ви не можете купити жодної одиниці.")
                        return

                    print(f"Максимальна кількість {asset}, яку ви можете купити: {int(max_amount)}")
                    amount = input_int(f"Скільки {asset} ви хочете купити? (максимум {int(max_amount)}): ")

                    # Перевірка на введення кількості, що перевищує максимальну
                    if amount > max_amount:
                        print(f"Ви не можете купити більше {int(max_amount)} {asset}.")
                    else:
                        self.buy(asset, amount)
                        print(f"Ви купили {amount} {asset}")
                        break
                else:
                    print(f"Неправильний вибір. Виберіть номер від 1 до {len(assets_list)}")
            except (WrongAssetName, NotEnoughCash) as exc:
                print(exc)

    def sell_action(self):
        """ Дія продажу активу через вибір зі списку наявних активів """
        owned_assets = [(asset, quantity) for asset, quantity in self.assets.items() if quantity > 0]
        if not owned_assets:
            print("У вас немає активів для продажу.")
            return

        print("Ваші активи:")
        for idx, (asset, quantity) in enumerate(owned_assets, 1):
            print(f"{idx}. {asset} - {quantity}шт")

        while True:
            try:
                # Вибір активу для продажу
                asset_idx = input_int("Виберіть актив для продажу за номером: ")
                if 1 <= asset_idx <= len(owned_assets):
                    asset, quantity = owned_assets[asset_idx - 1]

                    amount = input_int(f"Скільки {asset} ви хочете продати? (максимум {quantity}): ")

                    if amount > quantity:
                        print(f"Ви не можете продати більше {quantity} {asset}.")
                    else:
                        self.sell(asset, amount)
                        print(f"Ви продали {amount} {asset}")
                        break
                else:
                    print(f"Неправильний вибір. Виберіть номер від 1 до {len(owned_assets)}")
            except (WrongAssetName, NotEnoughAsset) as exc:
                print(exc)

    def print_result(self):
        profit = self.profit
        if profit > 0:
            print("Stonks! Ви завершили торгівлю з прибутком! Час сплатити податки!")
        elif profit == 0:
            print("Ну хоч не в мінус, це вже добре!")
        else:
            print("Not stonks! Ви закінчили торгівлю у збиток. Можливо, наступного разу буде краще!")


if __name__ == '__main__':
    from argparse import ArgumentParser
    import inspect
    import mode_config

    history_classes = {
        name.removesuffix('AssetPriceHistory').lower(): class_
        for name, class_ in inspect.getmembers(mode_config, inspect.isclass)
        if issubclass(class_, AssetPriceHistory) and class_ != AssetPriceHistory
    }

    parser = ArgumentParser()
    parser.add_argument(
        '--history',
        choices=history_classes.keys(),
        default='real',  # Встановлюємо 'real' як значення за замовчуванням
        help='Яку історію використовувати',
    )
    parser.add_argument(
        '--cash',
        type=Decimal,
        default=Decimal(100_000),
        help='Скільки грошей на початку',
    )
    args = parser.parse_args()

    # Заміна 'real' на обраний режим симуляції
    history_class = history_classes.get(args.history, RealAssetPriceHistory)
    simulator = PortfolioSimulator(
        history=history_class(),
        cash=args.cash,
    )
    simulator.run()
