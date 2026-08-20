from __future__ import annotations

from typing import Any

from growwapi import GrowwAPI

from groww_mcp.groww_client import GrowwClient


class ExtendedGrowwClient(GrowwClient):
  def _live(self, data: Any) -> dict[str, Any]:
    return {"mode": "live", "data": data}

  def get_user_profile(self) -> dict[str, Any]:
    return self._live(self._ensure_client().get_user_profile(timeout=15))

  def get_positions(self, segment: str | None = None) -> dict[str, Any]:
    seg = self._resolve_segment(segment) if segment else None
    return self._live(self._ensure_client().get_positions_for_user(segment=seg, timeout=15))

  def get_position_by_symbol(self, trading_symbol: str, segment: str = "CASH") -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_position_for_trading_symbol(
        trading_symbol=trading_symbol.upper(),
        segment=self._resolve_segment(segment),
        timeout=15,
      )
    )

  def get_margin(self) -> dict[str, Any]:
    return self._live(self._ensure_client().get_available_margin_details(timeout=15))

  def get_orders(self, segment: str | None = None, page: int = 0, page_size: int = 25) -> dict[str, Any]:
    seg = self._resolve_segment(segment) if segment else None
    return self._live(
      self._ensure_client().get_order_list(page=page, page_size=page_size, segment=seg, timeout=15)
    )

  def get_order_detail(self, groww_order_id: str, segment: str = "CASH") -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_order_detail(
        segment=self._resolve_segment(segment),
        groww_order_id=groww_order_id,
        timeout=15,
      )
    )

  def get_order_status(self, groww_order_id: str, segment: str = "CASH") -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_order_status(
        segment=self._resolve_segment(segment),
        groww_order_id=groww_order_id,
        timeout=15,
      )
    )

  def get_order_status_by_reference(self, order_reference_id: str, segment: str = "CASH") -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_order_status_by_reference(
        segment=self._resolve_segment(segment),
        order_reference_id=order_reference_id,
        timeout=15,
      )
    )

  def get_order_trades(self, groww_order_id: str, segment: str = "CASH") -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_trade_list_for_order(
        groww_order_id=groww_order_id,
        segment=self._resolve_segment(segment),
        timeout=15,
      )
    )

  def modify_order(
    self,
    groww_order_id: str,
    quantity: int,
    order_type: str = "LIMIT",
    segment: str = "CASH",
    price: float | None = None,
    trigger_price: float | None = None,
  ) -> dict[str, Any]:
    return self._live(
      self._ensure_client().modify_order(
        order_type=order_type.upper(),
        segment=self._resolve_segment(segment),
        groww_order_id=groww_order_id,
        quantity=quantity,
        price=price,
        trigger_price=trigger_price,
        timeout=15,
      )
    )

  def cancel_order(self, groww_order_id: str, segment: str = "CASH") -> dict[str, Any]:
    return self._live(
      self._ensure_client().cancel_order(
        groww_order_id=groww_order_id,
        segment=self._resolve_segment(segment),
        timeout=15,
      )
    )

  def place_order_full(
    self,
    trading_symbol: str,
    quantity: int,
    transaction_type: str = "BUY",
    order_type: str = "MARKET",
    exchange: str = "NSE",
    product: str = "CNC",
    segment: str = "CASH",
    price: float = 0.0,
    trigger_price: float | None = None,
    validity: str = "DAY",
  ) -> dict[str, Any]:
    return self._live(
      self._ensure_client().place_order(
        validity=validity.upper(),
        exchange=exchange.upper(),
        order_type=order_type.upper(),
        product=product.upper(),
        quantity=quantity,
        segment=self._resolve_segment(segment),
        trading_symbol=trading_symbol.upper(),
        transaction_type=transaction_type.upper(),
        price=price or None,
        trigger_price=trigger_price,
        timeout=15,
      )
    )

  def get_greeks(
    self,
    exchange: str,
    underlying: str,
    trading_symbol: str,
    expiry: str,
  ) -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_greeks(
        exchange=exchange.upper(),
        underlying=underlying.upper(),
        trading_symbol=trading_symbol.upper(),
        expiry=expiry,
      )
    )

  def get_historical_candles(
    self,
    exchange: str,
    segment: str,
    groww_symbol: str,
    start_time: str,
    end_time: str,
    candle_interval: str = "1day",
  ) -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_historical_candles(
        exchange=exchange.upper(),
        segment=self._resolve_segment(segment),
        groww_symbol=groww_symbol.upper(),
        start_time=start_time,
        end_time=end_time,
        candle_interval=candle_interval,
        timeout=15,
      )
    )

  def get_expiries(
    self,
    exchange: str,
    underlying_symbol: str,
    year: int | None = None,
    month: int | None = None,
  ) -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_expiries(
        exchange=exchange.upper(),
        underlying_symbol=underlying_symbol.upper(),
        year=year,
        month=month,
        timeout=15,
      )
    )

  def get_contracts(self, exchange: str, underlying_symbol: str, expiry_date: str) -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_contracts(
        exchange=exchange.upper(),
        underlying_symbol=underlying_symbol.upper(),
        expiry_date=expiry_date,
        timeout=15,
      )
    )

  def get_smart_orders(self, segment: str | None = None) -> dict[str, Any]:
    seg = self._resolve_segment(segment) if segment else GrowwAPI.SEGMENT_CASH
    return self._live(self._ensure_client().get_smart_order_list(segment=seg, timeout=15))

  def get_smart_order(self, smart_order_id: str, segment: str = "CASH", smart_order_type: str = "GTT") -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_smart_order(
        segment=self._resolve_segment(segment),
        smart_order_type=smart_order_type.upper(),
        smart_order_id=smart_order_id,
        timeout=15,
      )
    )

  def create_smart_order_gtt(
    self,
    trading_symbol: str,
    quantity: int,
    trigger_price: str,
    trigger_direction: str,
    transaction_type: str,
    exchange: str = "NSE",
    product_type: str = "CNC",
    segment: str = "CASH",
    order_type: str = "MARKET",
    price: str | None = None,
    duration: str = "DAY",
  ) -> dict[str, Any]:
    order = {"order_type": order_type.upper(), "transaction_type": transaction_type.upper()}
    if price is not None:
      order["price"] = price
    return self._live(
      self._ensure_client().create_smart_order(
        smart_order_type=GrowwAPI.SMART_ORDER_TYPE_GTT,
        segment=self._resolve_segment(segment),
        trading_symbol=trading_symbol.upper(),
        quantity=quantity,
        product_type=product_type.upper(),
        exchange=exchange.upper(),
        duration=duration.upper(),
        trigger_price=trigger_price,
        trigger_direction=trigger_direction.upper(),
        order=order,
        timeout=15,
      )
    )

  def modify_smart_order(
    self,
    smart_order_id: str,
    smart_order_type: str = "GTT",
    segment: str = "CASH",
    quantity: int | None = None,
    trigger_price: str | None = None,
  ) -> dict[str, Any]:
    return self._live(
      self._ensure_client().modify_smart_order(
        smart_order_id=smart_order_id,
        smart_order_type=smart_order_type.upper(),
        segment=self._resolve_segment(segment),
        quantity=quantity,
        trigger_price=trigger_price,
        timeout=15,
      )
    )

  def cancel_smart_order(
    self,
    smart_order_id: str,
    smart_order_type: str = "GTT",
    segment: str = "CASH",
  ) -> dict[str, Any]:
    return self._live(
      self._ensure_client().cancel_smart_order(
        segment=self._resolve_segment(segment),
        smart_order_type=smart_order_type.upper(),
        smart_order_id=smart_order_id,
        timeout=15,
      )
    )

  def search_instrument(self, exchange: str, trading_symbol: str) -> dict[str, Any]:
    return self._live(
      self._ensure_client().get_instrument_by_exchange_and_trading_symbol(
        exchange=exchange.upper(),
        trading_symbol=trading_symbol.upper(),
      )
    )

  def get_instrument_by_groww_symbol(self, groww_symbol: str) -> dict[str, Any]:
    return self._live(self._ensure_client().get_instrument_by_groww_symbol(groww_symbol.upper()))

  def calculate_order_margin(
    self,
    segment: str,
    trading_symbol: str,
    quantity: int,
    transaction_type: str,
    product: str = "CNC",
    order_type: str = "MARKET",
    exchange: str = "NSE",
    price: float = 0.0,
  ) -> dict[str, Any]:
    order = {
      "trading_symbol": trading_symbol.upper(),
      "transaction_type": transaction_type.upper(),
      "quantity": quantity,
      "order_type": order_type.upper(),
      "product": product.upper(),
      "exchange": exchange.upper(),
      "price": price,
    }
    return self._live(
      self._ensure_client().get_order_margin_details(
        segment=self._resolve_segment(segment),
        orders=[order],
        timeout=15,
      )
    )
