from rasa_sdk import FormValidationAction
from rasa_sdk.events import EventType
import requests
import datetime
from rasa_sdk.types import DomainDict
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction, AllSlotsReset
import phonenumbers
import re
from actions.servicesBot import *

sheet = read_file()
switchRequire = {'composition': 2,
                 'taste': 3,
                 'effects': 4,
                 'contraindications': 5,
                 'user_manual': 6,
                 'storage': 7,
                 'made_in': 8,
                 'sale': 9,
                 'price': 10,
                 'nominations': 11,
                 'recognizing_signs': 12,
                 'ship': 13,
                 'user_object': 14,
                 'year_gr1': 16,
                 'year_gr2': 17,
                 'year_gr3': 18,
                 }


# ----------------- Trả lời yêu cầu của khách về thông tin sản phẩm ------------------------#
class ActionAnswer(Action):

    def name(self) -> Text:
        return "action_answer"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if tracker.get_slot("product_name_en") is None:
            # nếu chưa nhận được tên sản phẩm sẽ yêu cầu khách hàng chọn sản phẩm cần tư vấn.
            dispatcher.utter_message(response="utter_ask_product_name_en")
        elif tracker.get_slot("request_counselling") is None:
            # Nếu chưa nhận được yêu cầu tư vấn từ khách sẽ hỏi khách cần tư vấn gì?
            dispatcher.utter_message(response="utter_ask_request_counselling")
        else:
            # Xử lý yêu cầu của khách
            requestCustom = str(tracker.get_slot("request_counselling"))
            productName = tracker.get_slot("product_name_en")
            content = "Rất xin lỗi!!!\nShop hiện chưa có thông tin về vấn đề này."
            if "bánh" in str(productName).lower():
                # Tư vấn theo sản phẩm Bánh dinh dưỡng Hebi
                if sheet["B" + requestCustom].value is not None:
                    # Nếu vị trí đó không có thông tin sẽ trả về content ban đầu.
                    content = str(sheet["B" + requestCustom].value)
            elif "men" in str(productName).lower():
                # Tư vấn theo sản phẩm Men vi khuẩn sống Việt Nhật
                if sheet["C" + requestCustom].value is not None:
                    content = str(sheet["C" + requestCustom].value)
            # Trả về thông tin khách yêu cầu
            dispatcher.utter_message(text=content)
            # reset slot request_counselling
            return [SlotSet("request_counselling", None)]
        return []


# ----------------- Form Đặt hàng------------------------#

class ActionOrderForm(Action):

    def name(self) -> Text:
        return "action_order_form"

    def run(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: Tracker,
            domain: "DomainDict",
    ) -> List[Dict[Text, Any]]:
        required_slots = ["phone", "name", "product_name_en", "amount", "province", "district", "ward"]
        for slot_name in required_slots:
            if tracker.get_slot(slot_name) is None:
                # nếu như có một thành phần nào đó rỗng thì sẽ phải điền đủ
                return [SlotSet("requested_slot", slot_name)]
        # nếu đã có giá trị mà hàm này đk gọi đến thì nó set slot này bằng None
        return [SlotSet("requested_slot", None)]
        # dispatcher.utter_message(text= tracker.get_slot("phone_number"))


# ----------------- Validate dữu liệu From ------------------------#
class ValidateActionOrderForm(FormValidationAction):
    id_province = ""
    id_district = ""
    header = {'token': '82a0da54-c84b-11eb-bb70-b6be8148d819', 'Content-Type': 'application/json'}

    def name(self) -> Text:
        return "validate_action_order_form"

    def province_db(self) -> List[dict]:
        r = requests.get(url='https://online-gateway.ghn.vn/shiip/public-api/master-data/province', headers=self.header)
        data = r.json()['data']
        list_province = []
        for province in data:
            try:
                prodict = {
                    "id_province": province['ProvinceID'],
                    "NameExtension": province['NameExtension']
                }
                list_province.append(dict(prodict))
            except:
                print("Có Tỉnh/Thành Đặc Biệt")
        return list_province

    def district_db(self) -> List[dict]:
        list_district = []
        if self.id_province:
            param = {'province_id': str(self.id_province)}
            r = requests.get(url='https://online-gateway.ghn.vn/shiip/public-api/master-data/district',
                             headers=self.header,
                             params=param)
            data = r.json()['data']
            for district in data:
                try:
                    disdic = {
                        "id_district": district['DistrictID'],
                        "NameExtension": district['NameExtension']
                    }
                    list_district.append(dict(disdic))
                except:
                    print("Có Quận/Huyện Đặc Biệt ", district)
        return list_district

    def ward_db(self) -> List[dict]:
        list_ward = []
        if self.id_district:
            param = {'district_id': str(self.id_district)}
            r = requests.get(url='https://online-gateway.ghn.vn/shiip/public-api/master-data/ward',
                             headers=self.header,
                             params=param)
            data = r.json()['data']
            for ward in data:
                try:
                    warddict = {
                        "NameExtension": ward['NameExtension']
                    }
                    list_ward.append(dict(warddict))
                except:
                    print("Có Xã/Phường Đặc Biệt")
        return list_ward

    def validate_province(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> List[EventType]:
        #  TODO
        list_district = ''
        for province in self.province_db():
            for namePro in province.get('NameExtension'):
                if slot_value[0].lower() in str(namePro).lower():
                    self.id_province = province['id_province']
                    # lấy danh sách huyện của Tỉnh
                    for district in self.district_db():
                        list_district += '\n' + district['NameExtension'][0]
                    print('Slot_province ', slot_value, "\nCác Huyện:\n", list_district)
                    dispatcher.utter_message(response="utter_list_district",
                                             list_district=list_district)
                    return {"province": slot_value[0], "district": None}
                else:
                    continue
        return {"province": None, "district": None}

    def validate_district(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> List[EventType]:
        list_ward = ''
        print('Slot_district ', slot_value)
        for district in self.district_db():
            for nameDis in district['NameExtension']:
                if slot_value[0].lower() in str(nameDis).lower():
                    print('Huyện: ', district, ' - ', slot_value[0])
                    self.id_district = district['id_district']
                    # lấy danh sách Xã của Huyện
                    for ward in self.ward_db():
                        list_ward += '\n' + ward['NameExtension'][0]
                    dispatcher.utter_message(response="utter_list_ward",
                                             list_ward=list_ward)
                    return {"district": slot_value[0]}
                else:
                    continue
        return {"district": None}

    def validate_ward(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> List[EventType]:
        for ward in self.ward_db():
            for nameWard in ward['NameExtension']:
                if slot_value[0].lower() in str(nameWard).lower():
                    print('Xã: ', ward, ' - ', slot_value[0])
                    print('Slot_ward ', slot_value)
                    return {"ward": slot_value[0]}
                else:
                    continue
        return {"ward": None}

    # Kiểm tra số điện thoại #

    def validate_phone(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> List[EventType]:
        #  TODO
        phone_number_list = str(tracker.get_slot('phone'))
        countSDT = False
        for match in phonenumbers.PhoneNumberMatcher(phone_number_list, "VN"):
            phone_number = str(match).split(' ')[2]
            countSDT = True
        if countSDT:
            # Lấy thông tin về tên và địa chỉ trong đơn hàng mới nhất của khách nếu có.(ID khách là phone_number)
            infoCustomer = get_familiar_customers(phone_number)
            if infoCustomer[0] is not None:
                address = str(infoCustomer[1]).split(', ')
                return {"phone": phone_number, "name": infoCustomer[0],
                        "ward": address[0], "district": address[1], "province": address[2]}
            else:
                return {"phone": phone_number}
        return {"phone": None}

    # Kiểm tra số lượng đặt hàng #
    def validate_amount(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> List[Dict[Text, Any]]:
        amount = str(tracker.get_slot('amount'))
        print(amount)
        amount = re.match(r'([^.0-9]*)?(\d{1,3})([^.0-9]*)?', amount)
        if amount:
            if int(amount.group(2)) > 0:
                return {"amount": amount.group(2)}
        return {"amount": None}


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
        a = '0'
        if "bánh" in str(tracker.get_slot("product_name_en")).lower():
            a = str(int(tracker.get_slot("amount")) * int(sheet["D10"].value))
        elif "men" in str(tracker.get_slot("product_name_en")).lower():
            a = str(int(tracker.get_slot("amount")) * int(sheet["E10"].value))
        dispatcher.utter_message(response="utter_order_details",
                                 name=tracker.get_slot("name"),
                                 phone=tracker.get_slot("phone"),
                                 amount=tracker.get_slot("amount"),
                                 product_name_en=tracker.get_slot("product_name_en"),
                                 total=str(a))
        return [SlotSet('total', a)]


# ----------------- Lưu đơn hàng ------------------------#

class ActionComfirm(Action):
    def name(self) -> Text:
        return "action_confirm_order"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # lấy thông tin đơn hàng từ slot
        name = str(tracker.get_slot("name"))
        phone = str(tracker.get_slot("phone"))
        product_name = str(tracker.get_slot("product_name_en"))
        amount = str(tracker.get_slot("amount"))
        total = str(tracker.get_slot("total"))
        date = str(datetime.datetime.today())
        address = str(tracker.get_slot("ward")) + ', ' + str(tracker.get_slot("district")) + ', ' + str(
            tracker.get_slot("province"))
        # Thêm 1 hàng giá trị vào file
        saveSuccess = save_order([name, phone, product_name, amount, total, date, address])
        # Hiển thị xác nhận đã lưu đơn
        if saveSuccess:
            dispatcher.utter_message(
                text="Đơn hàng của bạn đã được lưu lại✅\nShop sẽ liên hệ xác nhận trong vòng 24h, vui lòng chú ý điện thoại của bạn.\n")
        else:
            dispatcher.utter_message(
                text="Hệ thống đang bảo trì chức năng này. Xin lỗi vì sự bất tiện này! \nKhách hàng vui lòng trở lại sau 30 phút. \n")
        return [FollowupAction('action_reset_slot', None)]


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
        dispatcher.utter_message(text="Đơn hàng của bạn đã Huỷ bỏ!")
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
        if tracker.get_slot("age") is None:
            return [SlotSet("request_counselling", switchRequire.get('user_manual'))]
        else:
            age = int(tracker.get_slot("age"))
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
