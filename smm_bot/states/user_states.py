from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    waiting_for_link = State()
    waiting_for_quantity = State()
    confirming_order = State()


class TopUpStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_payment_proof = State()


class EarnStates(StatesGroup):
    waiting_for_promo = State()


class SupportStates(StatesGroup):
    waiting_for_message = State()


class NumberStates(StatesGroup):
    selecting_country = State()
    selecting_service = State()
    waiting_for_sms = State()


class AdminStates(StatesGroup):
    # Foydalanuvchi boshqaruvi
    waiting_for_user_id = State()
    waiting_for_balance_amount = State()
    waiting_for_user_message = State()

    # Xabar yuborish (Broadcast)
    waiting_for_broadcast = State()
    waiting_for_broadcast_message = State()

    # Promo kod
    waiting_for_promo_code = State()
    waiting_for_promo_amount = State()
    waiting_for_promo_uses = State()

    # Sozlamalar
    waiting_for_setting_value = State()

    # Support javoblari
    waiting_for_support_reply = State()

    # Buyurtma boshqaruvi
    waiting_for_order_id = State()