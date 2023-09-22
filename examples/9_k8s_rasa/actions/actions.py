from rasa_sdk import Action
from rasa_sdk.knowledge_base.storage import InMemoryKnowledgeBase
from rasa_sdk.knowledge_base.actions import ActionQueryKnowledgeBase
from rasa_sdk.events import SlotSet

# knowledge_base = json.load(open("../files/base_file"))

base_file = "/app/actions/base.json"

class ActionGreet(Action):
    def name(self):
        return "action_greet"

    def run(self,
            dispatcher,
            tracker,
            domain):
        name = next(tracker.get_latest_entity_values("PERSON"), None)
        print(name)
        if name:
            dispatcher.utter_message(text=f"你好呀，{name}")
        else:
            dispatcher.utter_message(text="你好呀")
        
class ActionSearchProducts(ActionQueryKnowledgeBase):
    def __init__(self):
        # load knowledge base with data from the given file
        knowledge_base = InMemoryKnowledgeBase(base_file)
        super().__init__(knowledge_base)

    def name(self):
        return "action_search_product"

    def run(self,
            dispatcher,
            tracker,
            domain):
        # knowledge_base = InMemoryKnowledgeBase("../files/base_file")
        result_product = []
        product_category = next(tracker.get_latest_entity_values("product_category"), tracker.get_slot("product_category"))
        skin = tracker.get_slot("skin") #适用肤质
        func = next(tracker.get_latest_entity_values("func"), tracker.get_slot("func")) #产品特点

        print(skin)
        print(product_category)
        print(func)
        categories_kb = list(set([i["品类"] for i in self.knowledge_base.data["product"]]))
        
        if product_category in categories_kb:
            if skin and func:
                for i in self.knowledge_base.data["product"]:
                    if (i["品类"] == product_category) and (skin in i["适用肤质"].split("，") or i["适用肤质"]=="所有肤质") and (func in i["产品特点"].split("，")):
                        result_product.append(i["产品名"])
            elif skin:
                for i in self.knowledge_base.data["product"]:
                    if (i["品类"] == product_category) and (skin in i["适用肤质"].split("，") or i["适用肤质"]=="所有肤质"):
                        result_product.append(i["产品名"])
            elif func:
                for i in self.knowledge_base.data["product"]:
                    if (i["品类"] == product_category) and (func in i["产品特点"].split("，")):
                        result_product.append(i["产品名"])
            else:
                for i in self.knowledge_base.data["product"]:
                    if i["品类"] == product_category:
                        result_product.append(i["产品名"])

            if len(result_product) == 0:
                if next(tracker.get_latest_entity_values("func"), None):
                    retmsg = "不好意思噢, 目前这种产品还在研发中, 敬请期待：）"
                else:
                    func = None
                    if skin:
                        for i in self.knowledge_base.data["product"]:
                            if (i["品类"] == product_category) and (skin in i["适用肤质"].split("，") or i["适用肤质"]=="所有肤质"):
                                result_product.append(i["产品名"])
                    else:
                        for i in self.knowledge_base.data["product"]:
                            if i["品类"] == product_category:
                                result_product.append(i["产品名"])
                    if len(result_product) == 0:
                        retmsg = "不好意思噢, 目前这种产品还在研发中, 敬请期待：）"
                    else:
                        template = "可以考虑看看我们这款产品噢：{0}"
                        retmsg = template.format(", ".join(result_product))

            else:
                template = "可以考虑看看我们这款产品噢：{0}"
                retmsg = template.format(", ".join(result_product))
            dispatcher.utter_message(retmsg)
        elif product_category:
            dispatcher.utter_message("知识库中暂无与 {0} 类型产品相关的记录".format(product_category))
        else: # 如果没有识别到想要询问的产品类别
            dispatcher.utter_message(f"我们有许多适合你的产品哦，请问你想要什么类型的呢？我们有{', '.join(categories_kb)}")
        return [SlotSet("skin", skin), SlotSet("result_product", result_product)]
    
class ActionRequestAttribute(ActionQueryKnowledgeBase):
    def __init__(self):
        # load knowledge base with data from the given file
        knowledge_base = InMemoryKnowledgeBase(base_file)
        super().__init__(knowledge_base)

    def name(self):
        return "action_request_attribute"

    def run(self,
            dispatcher,
            tracker,
            domain):
        """
        Utters a response that informs the user about the attribute value of the
        attribute of interest.
        Args:
            dispatcher: the dispatcher
            object_name: the name of the object
            attribute_name: the name of the attribute
            attribute_value: the value of the attribute
        """
        attribute_name = next(tracker.get_latest_entity_values("attribute"), None)
        current_product = next(tracker.get_latest_entity_values("product"), None)
        result_product = tracker.get_slot("result_product")
        products_kb = list(set([i["产品名"] for i in self.knowledge_base.data["product"]]))
        if current_product:
            current_product_attribute = None
            current_product_attribute_flag = None
            if current_product in products_kb:
                for i in self.knowledge_base.data["product"]:
                    if i["产品名"] == current_product:
                        if attribute_name in i.keys():
                            current_product_attribute = i[attribute_name]
                        else:
                            current_product_attribute_flag = "NA"
            else:
                current_product_attribute = None
            if current_product_attribute:
                dispatcher.utter_message(text = f"{current_product}的{attribute_name}是{current_product_attribute}")
            elif current_product_attribute_flag == "NA":
                dispatcher.utter_message(text = f"这款产品目前还没有{attribute_name}的相关记录哦~")
            else:
                dispatcher.utter_message(text = f"这款产品不在我们的数据库里哦~")
        elif result_product:
            text = ""
            text_l = []
            for prod in result_product:
                current_product_attribute = None
                for i in self.knowledge_base.data["product"]:
                    if i["产品名"] == prod:
                        if attribute_name in i.keys():
                            current_product_attribute = i[attribute_name]
                        else:
                            current_product_attribute_flag = "NA"
                if current_product_attribute:
                    text_l.append(f"{prod}的{attribute_name}是{current_product_attribute}")
                else:
                    text = f"这款产品不在我们的数据库里哦~"
            if text_l:
                text = ", ".join(text_l)
            dispatcher.utter_message(text = text)
        else:
            dispatcher.utter_message(text=f"我们有{products_kb}等，你需要询问哪个产品的{attribute_name}呢？")
        if current_product: 
            product = current_product
        else:
            product = result_product[0]
        return [SlotSet("attribute", attribute_name), SlotSet("from_product", product)]

class ActionCompareAttribute(ActionQueryKnowledgeBase):
    def __init__(self):
        # load knowledge base with data from the given file
        knowledge_base = InMemoryKnowledgeBase(base_file)
        super().__init__(knowledge_base)

    def name(self):
        return "action_compare_attribute"

    def run(self,
            dispatcher,
            tracker,
            domain):
        """
        Utters a response that informs the user about the attribute value of the
        attribute of interest.
        Args:
            dispatcher: the dispatcher
            object_name: the name of the object
            attribute_name: the name of the attribute
            attribute_value: the value of the attribute
        """
        attribute_name = next(tracker.get_latest_entity_values("attribute"), tracker.get_slot("attribute"))
        result_product = tracker.get_slot("result_product")
        current_product = next(tracker.get_latest_entity_values("product"), None)
        compare_from = tracker.get_slot("from_product")    
        
        comparing_products = list(set([current_product] + result_product + [compare_from]))
        attribute_dic = {item["产品名"]: item[attribute_name] for item in self.knowledge_base.data["product"] if item["产品名"] in comparing_products}
        if comparing_products:
            dispatcher.utter_message(text = f"这些产品的价格如下：{attribute_dic}")
        else:
            dispatcher.utter_message(text = "你想要比较哪些产品呢？")




