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

sheet = read_file()
switchRequire = {
    'Gia': '3',
    'composition': '4',
    'taste': '5',
    'effects': '6',
    'contraindications': '7',
    'user_manual': '8',
    'storage': '9',
    'made_in': '10',
    'sale': '11',
    'price': '12',
    'nominations': '13',
    'recognizing_signs': '14',
    'ship': '15',
    'user_object': '16',
    'year_gr1': '17',
    'year_gr2': '18',
    'year_gr3': '19',
    'Banh': 'B',
    'Men': 'C',
    'image': 'D'
}
isFamiliarCustomers = False


# ----------------- Trả lời yêu cầu của khách về thông tin sản phẩm ------------------------#
class ActionAnswer(Action):

    def name(self) -> Text:
        return "action_answer"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if tracker.get_slot("product_name") is None:
            # nếu chưa nhận được tên sản phẩm sẽ yêu cầu khách hàng chọn sản phẩm cần tư vấn.
            dispatcher.utter_message(response="utter_ask_product_name")
        elif tracker.get_slot("request_counselling") is None:
            # Nếu chưa nhận được yêu cầu tư vấn từ khách sẽ hỏi khách cần tư vấn gì?
            dispatcher.utter_message(response="utter_ask_request_counselling")
        else:
            # Xử lý yêu cầu của khách
            requestCustomA = switchRequire.get('Banh') + str(tracker.get_slot("request_counselling"))
            requestCustomB = switchRequire.get('Men') + str(tracker.get_slot("request_counselling"))
            image = switchRequire.get('image') + str(tracker.get_slot("request_counselling"))
            productName = tracker.get_slot("product_name")
            content = "Rất xin lỗi!!!\nShop hiện chưa có thông tin về vấn đề này."
            #
            if "bánh" in str(productName).lower():
                # Tư vấn theo sản phẩm Bánh dinh dưỡng Hebi
                if sheet[requestCustomA].value is not None:
                    # Nếu vị trí đó không có thông tin sẽ trả về content ban đầu.
                    content = str(sheet[requestCustomA].value)
            elif "men" in str(productName).lower():
                # Tư vấn theo sản phẩm Men vi khuẩn sống Việt Nhật
                if sheet[requestCustomB].value is not None:
                    content = str(sheet[requestCustomB].value)
            # Trả về thông tin khách yêu cầu
            dispatcher.utter_message(text=content, image=str(sheet[image].value))
            # reset slot request_counselling
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


# ----------------- Reset slot value------------------------#
class ValidateActionCustomerOrderForm(FormValidationAction):
    id_province = ""
    id_district = ""
    header = {'token': '82a0da54-c84b-11eb-bb70-b6be8148d819', 'Content-Type': 'application/json'}
    urlApi = 'https://online-gateway.ghn.vn/shiip/public-api/master-data/'

    def name(self) -> Text:
        return "validate_customer_order_form"

    @staticmethod
    def province_db(self) -> List[dict]:
        r = requests.get(url=self.urlApi + 'province', headers=self.header)
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

    @staticmethod
    def district_db(self) -> List[dict]:
        list_district = []
        if self.id_province:
            param = {'province_id': str(self.id_province)}
            r = requests.get(url=self.urlApi + 'district',
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

    @staticmethod
    def ward_db(self) -> List[dict]:
        list_ward = []
        if self.id_district:
            param = {'district_id': str(self.id_district)}
            r = requests.get(url=self.urlApi + 'ward',
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
        list_district = ''
        for province in self.province_db():
            for namePro in province.get('NameExtension'):
                if slot_value[0].lower() in str(namePro).lower():
                    self.id_province = province['id_province']
                    # lấy danh sách huyện của Tỉnh
                    for district in self.district_db():
                        list_district += '\n' + district['NameExtension'][0]
                    print('Slot province_name ', slot_value)
                    if not isFamiliarCustomers:
                        dispatcher.utter_message(response="utter_list_district",
                                                 list_district=list_district)
                    return {"province_name": slot_value[0]}
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
        list_ward = ''
        print('Slot district_name: ', slot_value)
        for district in self.district_db():
            for nameDis in district['NameExtension']:
                if slot_value[0].lower() in str(nameDis).lower():
                    print('Huyện: ', district, ' - ', slot_value[0])
                    self.id_district = district['id_district']
                    # lấy danh sách Xã của Huyện
                    for ward in self.ward_db():
                        list_ward += '\n' + ward['NameExtension'][0]
                    if not isFamiliarCustomers:
                        dispatcher.utter_message(response="utter_list_ward",
                                                 list_ward=list_ward)
                    return {"district_name": slot_value[0]}
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
        for ward in self.ward_db():
            for nameWard in ward['NameExtension']:
                if slot_value[0].lower() in str(nameWard).lower():
                    print('Xã: ', ward, ' - ', slot_value[0])
                    print('Slot ward_name: ', slot_value)
                    return {"ward_name": slot_value[0]}
                else:
                    continue
        return {"ward_name": None}

    # Kiểm tra số điện thoại #

    def validate_customer_phone_number(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Dict[Text, Any]:
        #  TODO
        global isFamiliarCustomers
        phone_number_list = str(tracker.get_slot('phone'))
        phone_number = None
        # valid SDT và Tách lấy SDT
        for match in phonenumbers.PhoneNumberMatcher(phone_number_list, "VN"):
            phone_number = str(match).split(' ')[2]
        if phone_number is not None:
            # Lấy thông tin về tên và địa chỉ trong đơn hàng mới nhất của khách nếu có.(ID khách là phone_number)
            infoCustomer = get_familiar_customers(phone_number)
            if infoCustomer[0] is not None:
                isFamiliarCustomers = True
                address = str(infoCustomer[1]).split(', ')
                return {"customer_phone_number": phone_number, "customer_name": infoCustomer[0],
                        "province_name": address[2], "district_name": address[1],
                        "ward_name": address[0]}
            else:
                isFamiliarCustomers = False
                return {"customer_phone_number": phone_number}
        return {"customer_phone_number": None}

    # Kiểm tra số lượng đặt hàng #
    def validate_number_of_products(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Dict[Text, Any]:
        amount = str(tracker.get_slot('number_of_products'))
        print('Slot number_of_products: ', amount)
        amount = re.findall(r'\d+', str(slot_value))
        if amount is not None:
            if int(amount[0]) > 0:
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
        age = re.findall(r'\d+', str(slot_value))
        if age is not None:
            # validation succeeded, set the value of the "age" slot to value
            if 'tuổi' in slot_value:
                return {"age": age[0]}
            elif 'tháng' or 'm' or 'thag' in slot_value:
                return {"age": float(float(age[0]) / 12)}
            else:
                return {"age": None}
        else:
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
        price = 0
        total = ''
        if "bánh" in str(tracker.get_slot("product_name_en")).lower():
            price = int(sheet[switchRequire.get('Banh') + switchRequire.get('Gia')].value)
        elif "men" in str(tracker.get_slot("product_name_en")).lower():
            price = int(sheet[switchRequire.get('Men') + switchRequire.get('Gia')].value)
        amount = tracker.get_slot("number_of_products")
        if amount:
            total = str(amount * price)
        dispatcher.utter_message(response="utter_order_details", total=total, )
        return [SlotSet('total', total)]


# ----------------- Lưu đơn hàng ------------------------#

class ActionComfirm(Action):
    def name(self) -> Text:
        return "action_confirm_order"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # lấy thông tin đơn hàng từ slot
        name = str(tracker.get_slot("customer_name"))
        phone = str(tracker.get_slot("customer_phone_number"))
        product_name = str(tracker.get_slot("product_name"))
        amount = str(tracker.get_slot("number_of_products"))
        total = str(tracker.get_slot("total"))
        date = str(datetime.datetime.today())
        address = str(tracker.get_slot("ward_name")) + ', ' + str(tracker.get_slot("district_name")) + ', ' + str(
            tracker.get_slot("province_name"))
        # Thêm 1 hàng giá trị vào file
        saveSuccess = save_order(name, phone, product_name, amount, total, date, address)
        # Hiển thị xác nhận đã lưu đơn
        if saveSuccess:
            dispatcher.utter_message(
                text="Đơn hàng của bạn đã được lưu lại✅\nShop sẽ liên hệ xác nhận trong vòng 24h, vui lòng chú ý điện thoại của bạn.\n")
        else:
            dispatcher.utter_message(
                text="Hệ thống đang bảo trì chức năng này. Xin lỗi vì sự bất tiện này! \nKhách hàng vui lòng trở lại sau 30 phút. \n")
        return [AllSlotsReset()]


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
        return [AllSlotsReset()]


# ----------------- 1 Set value slot hỏi thành phần sản phẩm ------------------------#
class ActionSetSlotComposition(Action):

    def name(self) -> Text:
        return "action_set_slot_composition"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('composition'))]


# ----------------- 2  Set value slot hỏi Hương vị ------------------------#
class ActionSetSlotTaste(Action):

    def name(self) -> Text:
        return "action_set_slot_taste"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('taste'))]


# ----------------- 3  Set value slot hỏi công dụng ------------------------#
class ActionSetSlotEffects(Action):

    def name(self) -> Text:
        return "action_set_slot_effects"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('effects'))]


# ----------------- 4  Set value slot Chống chỉ định ------------------------#
class ActionSetSlotContraindications(Action):

    def name(self) -> Text:
        return "action_set_slot_contraindications"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('contraindications'))]


# ----------------- 5  Set value slot hỏi Hướng dẫn sử dụng------------------------#
class ActionSetSlotUserManual(Action):

    def name(self) -> Text:
        return "action_set_slot_user_manual"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        print('Slot Age: ', tracker.get_slot("age"))
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
            return [SlotSet("request_counselling", switchRequire.get('year_gr1'))]
        elif age > 15:
            return [SlotSet("request_counselling", switchRequire.get('year_gr3'))]
        else:
            return [SlotSet("request_counselling", switchRequire.get('year_gr2'))]


# ----------------- 6  Set value slot Hạn sử dụng------------------------#
class ActionSetSlotStorage(Action):

    def name(self) -> Text:
        return "action_set_slot_storage"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('storage'))]


# ----------------- 7  Set value slot Xuất sứ------------------------#
class ActionSetSlotMadeIn(Action):

    def name(self) -> Text:
        return "action_set_slot_made_in"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('made_in'))]


# ----------------- 8  Set value slot Chương trình giảm giá------------------------#
class ActionSetSlotSale(Action):

    def name(self) -> Text:
        return "action_set_slot_sale"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('sale'))]


# ----------------- 9  Set value slot Giá------------------------#
class ActionSetSlotPrice(Action):

    def name(self) -> Text:
        return "action_set_slot_price"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('price'))]


# ----------------- 10  Set value slot Đề cử sản phẩm dùng kèm theo ------------------------#
class ActionSetSlotNominations(Action):

    def name(self) -> Text:
        return "action_set_slot_nominations"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('nominations'))]


# ----------------- 11  Set value slot Dấu hiệu nhận biết------------------------#
class ActionSetSlotRecognizingSigns(Action):

    def name(self) -> Text:
        return "action_set_slot_recognizing_signs"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('recognizing_signs'))]


# ----------------- 12  Set value slot Giao hàng------------------------#
class ActionSetSlotShip(Action):

    def name(self) -> Text:
        return "action_set_slot_ship"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('ship'))]


# ----------------- 13  Set value slot Người dùng------------------------#
class ActionSetSlotUserObject(Action):

    def name(self) -> Text:
        return "action_set_slot_user_object"

    async def run(self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # custom behavior
        return [SlotSet("request_counselling", switchRequire.get('user_object'))]
