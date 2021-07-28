import datetime
import re

import phonenumbers
import requests
from rasa_sdk.types import DomainDict
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, AllSlotsReset, EventType
from actions.servicesBot import *

# TODO from actions.servicesBot import *
database = 'OnlineShop'  # tableName: Product, Receipt, Detail_Receipt, User_Manual, Customer
# infoProduct = get_db('SELECT * FROM {}.dbo.Product'.format(database))
# infoUserManual = get_db('SELECT * FROM {}.dbo.User_Manual'.format(database))
isUserManual = False
idProduct = None
idCustomer = None
switchRequire = {
    'id': 0,
    'name': 1,
    'price': 2,
    'effects': 3,
    'composition': 4,
    'contraindications': 5,
    'storage': 6,
    'made_in': 7,
    'recognizing_signs': 8,
    'sale': 9,
    'ship': 10,
    'user_object': 11,
    'product_quantity': 12,
    'priceText': 14,
    'year_gr1': 1,
    'year_gr2': 2,
    'year_gr3': 3
}


def approximate_string(str1, str2):
    count = 0
    var = str1.split(' ')
    var2 = str2.split(' ')
    if str1 == str2:
        return True
    for i in var:
        if i in str2:
            count += 1
    if count and len(var2) > 1:
        return True
    if count and len(var2) == 1:
        return True
    return False


def check_product_name(product_name, info_product):
    global idProduct
    for row in info_product:
        if approximate_string(str(product_name).lower(), str(row[switchRequire.get('name')]).lower()):
            idProduct = row[switchRequire.get('id')]
            return True
    return False


''' ----------------- Trả lời yêu cầu của khách về thông tin sản phẩm ---------------------'''


class ActionAnswer(Action):

    def name(self) -> Text:
        return "action_answer"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # TODO get_db in action_answer
        infoProduct = get_db('SELECT * FROM {}.dbo.Product'.format(database))
        global isUserManual
        productName = tracker.get_slot("product_name")
        requestCounselling = tracker.get_slot("request_counselling")
        print('Slot_was_set:\n\t"product_name" = {}\n\t"request_counselling" = {}'.format(
            productName, requestCounselling))
        if productName is None:
            # Khi chưa nhận được tên sản phẩm
            dispatcher.utter_message(response="utter_ask_product_name")
        elif check_product_name(productName, infoProduct) is False:
            # Khi nhận được sản phẩm không kinh doanh
            dispatcher.utter_message(response="utter_ask_product_name",
                                     text='Hiện Shop không có kinh doanh sản phẩm này! Mời bạn tham khảo các sản phẩm dưới đây')
            return [SlotSet("product_name", None)]
        elif requestCounselling is None:
            # Khi chưa nhận được yêu cầu khách
            dispatcher.utter_message(response="utter_ask_request_counselling")
        else:
            # Xử lý yêu cầu của khách
            content = None
            for row in infoProduct:
                print(productName, row[switchRequire.get('name')], isUserManual)
                if approximate_string(str(productName).lower(), str(row[switchRequire.get('name')]).lower()):

                    if isUserManual is False:
                        print('Content: Yes')
                        content = row[requestCounselling]
                        break
                    else:
                        # TODO get_db
                        infoUserManual = get_db('SELECT * FROM {}.dbo.User_Manual'.format(database))
                        for row2 in infoUserManual:
                            if row[switchRequire.get('id')] == row2[switchRequire.get('id')]:
                                print('Content: UserManual', row2[requestCounselling])
                                content = row2[requestCounselling]
                                isUserManual = False
                                break
                        break
            if content is None:
                content = "Dạ Shop hiện chưa có thông tin về vấn đề này."
            # Trả về thông tin khách yêu cầu
            dispatcher.utter_message(text=content, response="utter_request_counselling")
            return [SlotSet("request_counselling", None)]
        return []


# ----------------- Form Đặt hàng------------------------#

class ActionCustomerOrderForm(Action):

    def name(self) -> Text:
        return "customer_order_form"

    def run(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: Tracker,
            domain: "DomainDict",
    ) -> List[Dict[Text, Any]]:
        required_slots = ["customer_phone_number", "customer_name", "product_name", "number_of_products",
                          "province_name", "district_name", "ward_name"]
        for slot_name in required_slots:
            if tracker.get_slot(slot_name) is None:
                # nếu như có một thành phần nào đó rỗng thì sẽ phải điền đủ
                return [SlotSet("requested_slot", slot_name)]
        # nếu đã có giá trị mà hàm này đk gọi đến thì nó set slot này bằng None
        return [SlotSet("requested_slot", None)]
        # dispatcher.utter_message(text= tracker.get_slot("phone_number"))


# ----------------- Validate ------------------------#
class ValidateActionCustomerOrderForm(FormValidationAction):
    id_province = ""
    id_district = ""
    header = {'token': '82a0da54-c84b-11eb-bb70-b6be8148d819', 'Content-Type': 'application/json'}
    urlApi = 'https://online-gateway.ghn.vn/shiip/public-api/master-data/'

    def name(self) -> Text:
        return "validate_customer_order_form"

    def province_db(self) -> List[dict]:
        r = requests.get(
            url=(self.urlApi + 'province'),
            headers=self.header)
        data = r.json()['data']
        list_province = []
        for province in data:
            try:
                provinceName = {
                    "id_province": province['ProvinceID'],
                    "NameExtension": province['NameExtension']
                }
                list_province.append(dict(provinceName))
            except Exception as e:
                print("Có Tỉnh/Thành Đặc Biệt", e.args)
        return list_province

    def district_db(self) -> List[dict]:
        list_district = []
        if self.id_province:
            param = {'province_id': str(self.id_province)}
            r = requests.get(
                url=(self.urlApi + 'district'),
                headers=self.header,
                params=param)
            data = r.json()['data']
            for district in data:
                try:
                    districtName = {
                        "id_district": district['DistrictID'],
                        "NameExtension": district['NameExtension']
                    }
                    list_district.append(dict(districtName))
                except Exception as e:
                    print("Có Quận/Huyện Đặc Biệt ", e.args)
        return list_district

    def ward_db(self) -> List[dict]:
        list_ward = []
        if self.id_district:
            param = {'district_id': str(self.id_district)}
            r = requests.get(
                url=(self.urlApi + 'ward'),
                headers=self.header,
                params=param)
            data = r.json()['data']
            for ward in data:
                try:
                    wardName = {
                        "NameExtension": ward['NameExtension']
                    }
                    list_ward.append(dict(wardName))
                except Exception as e:
                    print("Có Xã/Phường Đặc Biệt", e.args)
        return list_ward

    def validate_province_name(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Dict[Text, Any]:
        """ Validate province value."""
        print('Slot province_name ', slot_value)
        for province in self.province_db():
            for namePro in province.get('NameExtension'):
                if slot_value.lower() in str(namePro).lower():
                    self.id_province = province['id_province']
                    print('Slot_was_set: "province_name" = ', slot_value)
                    return {"province_name": slot_value}
                else:
                    continue
        return {"province_name": None}

    def validate_district_name(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Dict[Text, Any]:
        """ Validate district value."""
        print('Slot district_name: ', slot_value)
        for district in self.district_db():
            for nameDis in district['NameExtension']:
                if slot_value.lower() in str(nameDis).lower():
                    self.id_district = district['id_district']
                    print('Slot_was_set: "district_name" = ', slot_value)
                    return {"district_name": slot_value}
                else:
                    continue
        return {"district_name": None}

    def validate_ward_name(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Dict[Text, Any]:
        """ Validate ward value."""
        print('Slot ward_name: ', slot_value)
        for ward in self.ward_db():
            for nameWard in ward['NameExtension']:
                print(nameWard)
                if slot_value.lower() in str(nameWard).lower():
                    print('Slot_was_set: "ward_name" = ', slot_value)
                    return {"ward_name": slot_value}
                else:
                    continue
        return {"ward_name": None}

    def validate_product_name(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Dict[Text, Any]:
        """ Validate product_name value."""
        # TODO
        infoProduct = get_db('SELECT * FROM {}.dbo.Product'.format(database))
        print('Slot product_name: ', slot_value)
        if check_product_name(slot_value, infoProduct):
            print('Slot_was_set: "product_name" = ', slot_value)
            return {"product_name": slot_value}
        return {"product_name": None}

    def validate_customer_phone_number(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Dict[Text, Any]:
        phone_number = None
        print('Slot customer_phone_number: ', slot_value)
        # valid SDT và Tách lấy SDT
        for match in phonenumbers.PhoneNumberMatcher(slot_value, "VN"):
            phone_number = match
        if phone_number is not None:
            # Lấy thông tin về tên và địa chỉ trong đơn hàng mới nhất của khách nếu có.(ID khách là phone_number)
            #  TODO select_old_customers in validate_customer_phone_number
            infOldCustomer = select_old_customers(slot_value)
            if infOldCustomer is not None:
                global idCustomer
                idCustomer = infOldCustomer[4]
                return {"customer_phone_number": slot_value, "customer_name": infOldCustomer[0],
                        "province_name": infOldCustomer[1], "district_name": infOldCustomer[2],
                        "ward_name": infOldCustomer[3]}
            else:
                print('Slot_was_set: "customer_phone_number" = ', slot_value)
                return {"customer_phone_number": slot_value}
        return {"customer_phone_number": None}

    # Kiểm tra số lượng đặt hàng #
    def validate_number_of_products(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Dict[Text, Any]:
        print('Slot number_of_products: ', slot_value)
        amount = re.findall(r'\d+', str(slot_value))
        if amount is not None:
            if int(amount[0]) > 0:
                print('Slot_was_set: "number_of_products" = ', amount[0])
                return {"number_of_products": amount[0]}
        return {"number_of_products": None}

    @staticmethod
    def validate_age(
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate age value."""
        print('Slot number_of_products: ', slot_value)
        age = re.findall(r'\d+', str(slot_value))
        if age is not None:
            # validation succeeded, set the value of the "age" slot to value
            if 'tuổi' in slot_value:
                print('Slot_was_set: "number_of_products" = ', age[0])
                return {"age": age[0]}
            elif 'tháng' or 'm' or 'thag' in slot_value:
                print('Slot_was_set: "number_of_products" = ', float(float(age[0]) / 12))
                return {"age": float(float(age[0]) / 12)}
        # validation failed, set this slot to None so that the
        # user will be asked for the slot again
        return {"age": None}


# ----------------- View chi tiết đơn hàng ------------------------#

class ActionSubmit(Action):

    def name(self) -> Text:
        return "action_submit"

    def run(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: Tracker,
            domain: "DomainDict",
    ) -> List[Dict[Text, Any]]:
        # TODO get_db in action_submit
        infoProduct = get_db('SELECT * FROM {}.dbo.Product'.format(database))
        productName = tracker.get_slot("product_name")
        amount = tracker.get_slot("number_of_products")
        price = 0
        total = None
        for row in infoProduct:
            if str(productName).lower() in str(row[switchRequire.get('name')]).lower():
                price = float(row[switchRequire.get('price')])
                break
        if amount is not None:
            print('Price = ', price)
            total = str(int(amount) * price)
        dispatcher.utter_message(response="utter_order_details", total=total)
        print('Slot_was_set: "total" = ', total)
        return [SlotSet('total', total)]


# ----------------- Lưu đơn hàng ------------------------#

class ActionConfirm(Action):
    def name(self) -> Text:
        return "action_confirm_order"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # lấy thông tin đơn hàng từ slot
        address = tracker.get_slot("ward_name") + ', ' + tracker.get_slot("district_name") + ', ' + tracker.get_slot(
            "province_name")
        data_insert = [idCustomer, tracker.get_slot("customer_phone_number"), tracker.get_slot("customer_name"),
                       address, tracker.get_slot("total"), tracker.get_slot("number_of_products"), idProduct]
        # Thêm 1 hàng giá trị vào file
        # TODO in action_confirm_order
        saveSuccess = insert_order(data_insert)
        # customerName, customerPhoneNumber, productName, amount, total, date, address
        # Hiển thị xác nhận đã lưu đơn
        if saveSuccess:
            dispatcher.utter_message(
                text="Đơn hàng của bạn đã được lưu lại✅\nShop sẽ liên hệ xác nhận trong vòng 24h, vui lòng chú ý điện thoại của bạn.\n")
            return [AllSlotsReset()]
        else:
            dispatcher.utter_message(
                text="Hệ thống đang bảo trì chức năng này. Xin lỗi vì sự bất tiện này! \nKhách hàng vui lòng trở lại sau 30 phút. \n")
            return []


# ----------------- Reset slot value------------------------#
class ActionResetSlot(Action):
    def name(self) -> Text:
        return "action_reset_slot"

    def run(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: Tracker,
            domain: "DomainDict",
    ) -> List[Dict[Text, Any]]:
        global isFamiliarCustomers
        isFamiliarCustomers = False
        print('Reset All Slots successful!')
        return [AllSlotsReset()]


# ----------------- 1 Set value slot hỏi thành phần sản phẩm ------------------------#
class ActionSetSlotComposition(Action):

    def name(self) -> Text:
        return "action_set_slot_composition"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Thành phẩn)'.format(switchRequire.get('composition')))
        return [SlotSet("request_counselling", switchRequire.get('composition'))]


# ----------------- 3  Set value slot hỏi công dụng ------------------------#
class ActionSetSlotEffects(Action):

    def name(self) -> Text:
        return "action_set_slot_effects"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Công dụng)'.format(switchRequire.get('effects')))
        return [SlotSet("request_counselling", switchRequire.get('effects'))]


# ----------------- 4  Set value slot Chống chỉ định ------------------------#
class ActionSetSlotContraindications(Action):

    def name(self) -> Text:
        return "action_set_slot_contraindications"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Lưu ý)'.format(switchRequire.get('contraindications')))
        return [SlotSet("request_counselling", switchRequire.get('contraindications'))]


# ----------------- 5  Set value slot hỏi Hướng dẫn sử dụng------------------------#
class ActionSetSlotUserManual(Action):

    def name(self) -> Text:
        return "action_set_slot_user_manual"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot Age: ', tracker.get_slot("age"))
        global isUserManual
        isUserManual = True
        slot_value = tracker.get_slot("age")
        ageFull = re.findall(r'\d+', str(slot_value))
        if ageFull and slot_value is not None:
            # validation succeeded, set the value of the "age" slot to value
            if 'tháng' or 'm' or 'thag' or 'tháng tuổi' or 'month' in slot_value:
                age = float(float(ageFull[0]) / 12)
            else:
                age = float(ageFull[0])
        else:
            dispatcher.utter_message(response="utter_ask_age")
            return []

        if age < 2:
            print('Slot_was_set: request_counselling = {} (Cách dùng) Age = {}'.format(switchRequire.get('year_gr1'),
                                                                                       age))
            return [SlotSet("request_counselling", switchRequire.get('year_gr1'))]
        elif age > 15:
            print('Slot_was_set: request_counselling = {} (Cách dùng) Age = {}'.format(switchRequire.get('year_gr3'),
                                                                                       age))
            return [SlotSet("request_counselling", switchRequire.get('year_gr3'))]
        else:
            print('Slot_was_set: request_counselling = {} (Cách dùng) Age = {}'.format(switchRequire.get('year_gr2'),
                                                                                       age))
            return [SlotSet("request_counselling", switchRequire.get('year_gr2'))]


# ----------------- 6  Set value slot Hạn sử dụng------------------------#
class ActionSetSlotStorage(Action):

    def name(self) -> Text:
        return "action_set_slot_storage"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Bảo quản)'.format(switchRequire.get('storage')))
        return [SlotSet("request_counselling", switchRequire.get('storage'))]


# ----------------- 7  Set value slot Xuất sứ------------------------#
class ActionSetSlotMadeIn(Action):

    def name(self) -> Text:
        return "action_set_slot_made_in"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Xuất sứ)'.format(switchRequire.get('made_in')))
        return [SlotSet("request_counselling", switchRequire.get('made_in'))]


# ----------------- 8  Set value slot Chương trình giảm giá------------------------#
class ActionSetSlotSale(Action):

    def name(self) -> Text:
        return "action_set_slot_sale"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Giảm giá)'.format(switchRequire.get('sale')))
        return [SlotSet("request_counselling", switchRequire.get('sale'))]


# ----------------- 9  Set value slot Giá------------------------#
class ActionSetSlotPrice(Action):

    def name(self) -> Text:
        return "action_set_slot_price"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Giá)'.format(switchRequire.get('priceText')))
        return [SlotSet("request_counselling", switchRequire.get('priceText'))]


# ----------------- 11  Set value slot Dấu hiệu nhận biết------------------------#
class ActionSetSlotRecognizingSigns(Action):

    def name(self) -> Text:
        return "action_set_slot_recognizing_signs"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Nhận biết)'.format(switchRequire.get('recognizing_signs')))
        return [SlotSet("request_counselling", switchRequire.get('recognizing_signs'))]


# ----------------- 12  Set value slot Giao hàng------------------------#
class ActionSetSlotShip(Action):

    def name(self) -> Text:
        return "action_set_slot_ship"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Giao hàng)'.format(switchRequire.get('ship')))
        return [SlotSet("request_counselling", switchRequire.get('ship'))]


# ----------------- 13  Set value slot Người dùng------------------------#
class ActionSetSlotUserObject(Action):

    def name(self) -> Text:
        return "action_set_slot_user_object"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot_was_set: request_counselling = {} (Người dùng)'.format(switchRequire.get('user_object')))
        return [SlotSet("request_counselling", switchRequire.get('user_object'))]


# ----------------- 13  Set value slot Người dùng------------------------#
class ActionSetSlotProductQuantity(Action):

    def name(self) -> Text:
        return "action_set_slot_product_quantity"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print(
            'Slot_was_set: request_counselling = {} (Số lượng item/1 SP)'.format(switchRequire.get('product_quantity')))
        return [SlotSet("request_counselling", switchRequire.get('product_quantity'))]
