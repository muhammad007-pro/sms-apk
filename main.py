import os
import pandas as pd
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
from kivy.uix.popup import Popup

# Android specific imports
if platform == 'android':
    from jnius import autoclass
    from android.permissions import request_permissions, Permission
    SmsManager = autoclass('android.telephony.SmsManager')
else:
    # Mocking for development on PC
    class SmsManager:
        @staticmethod
        def getDefault():
            return SmsManager()
        def sendTextMessage(self, recipient, sc, message, sentIntent, deliveryIntent):
            print(f"[MOCK SMS] Yuborildi: {recipient} -> {message}")
        def divideMessage(self, message):
            # Mocking Java ArrayList-like behavior for size()
            class MockList(list):
                def size(self):
                    return len(self)
            return MockList([message])
        def sendMultipartTextMessage(self, recipient, sc, parts, sentIntents, deliveryIntents):
            print(f"[MOCK SMS Multi] Yuborildi: {recipient} -> {parts}")

class BulkSmsApp(App):
    def build(self):
        self.title = "Bulk SMS Auto-Sender (Uzbek)"
        self.contacts = {}  # {Group: [numbers]}
        self.sending_queue = []
        self.current_index = 0
        self.success_count = 0
        self.fail_count = 0
        self.current_group = ""
        self.log_entries = []

        if platform == 'android':
            request_permissions([
                Permission.SEND_SMS,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])

        # Main Layout
        root = BoxLayout(orientation='vertical', padding=20, spacing=15)

        # File path input
        root.add_widget(Label(text="Excel fayl manzili:", size_hint_y=None, height=30, halign='left'))
        self.file_path_input = TextInput(
            text="/sdcard/kontaktlar.xlsx",
            multiline=False,
            size_hint_y=None,
            height=50,
            hint_text="/sdcard/kontaktlar.xlsx"
        )
        root.add_widget(self.file_path_input)

        # Load button
        btn_load = Button(
            text="Excel Faylni Yuklash",
            size_hint_y=None,
            height=60,
            background_color=(0.2, 0.6, 1, 1)
        )
        btn_load.bind(on_release=self.load_excel)
        root.add_widget(btn_load)

        # Group Selection
        root.add_widget(Label(text="Guruhni tanlang:", size_hint_y=None, height=30))
        self.group_spinner = Spinner(
            text="Guruh tanlanmagan",
            values=(),
            size_hint_y=None,
            height=50
        )
        root.add_widget(self.group_spinner)

        # SMS Template
        root.add_widget(Label(text="SMS matni:", size_hint_y=None, height=30))
        self.sms_template = TextInput(
            hint_text="SMS shablon matnini kiriting...",
            multiline=True,
            size_hint_y=None,
            height=150
        )
        root.add_widget(self.sms_template)

        # Interval
        root.add_widget(Label(text="Interval (soniya):", size_hint_y=None, height=30))
        self.interval_input = TextInput(
            text="5",
            multiline=False,
            input_filter='int',
            size_hint_y=None,
            height=50
        )
        root.add_widget(self.interval_input)

        # Send Button
        self.btn_send = Button(
            text="Guruhga SMS Yuborishni Boshlash",
            size_hint_y=None,
            height=70,
            background_color=(0.1, 0.8, 0.1, 1)
        )
        self.btn_send.bind(on_release=self.start_sending)
        root.add_widget(self.btn_send)

        # Status Label
        self.status_label = Label(
            text="Tayyor",
            size_hint_y=None,
            height=40,
            color=(1, 1, 0, 1)
        )
        root.add_widget(self.status_label)

        return root

    def load_excel(self, instance):
        path = self.file_path_input.text.strip()
        if not os.path.exists(path):
            self.show_popup("Xatolik", f"Fayl topilmadi: {path}")
            return

        try:
            # Read Excel or CSV
            if path.endswith('.xlsx') or path.endswith('.xls'):
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path)

            if 'Guruh' not in df.columns or 'Raqam' not in df.columns:
                self.show_popup("Xatolik", "Excel faylda 'Guruh' va 'Raqam' ustunlari bo'lishi shart!")
                return

            # Dynamic grouping
            self.contacts = {}
            for index, row in df.iterrows():
                guruh = str(row['Guruh']).strip()
                raqam = str(row['Raqam']).strip()
                if guruh not in self.contacts:
                    self.contacts[guruh] = []
                self.contacts[guruh].append(raqam)

            self.group_spinner.values = list(self.contacts.keys())
            if self.group_spinner.values:
                self.group_spinner.text = self.group_spinner.values[0]
            
            self.show_popup("Muvaffaqiyat", f"Ma'lumotlar yuklandi. {len(self.contacts)} ta guruh topildi.")
            self.status_label.text = f"Yuklandi: {len(df)} ta kontakt"

        except Exception as e:
            self.show_popup("Xatolik", f"Faylni o'qishda xato: {str(e)}")

    def start_sending(self, instance):
        guruh = self.group_spinner.text
        if guruh == "Guruh tanlanmagan" or guruh not in self.contacts:
            self.show_popup("Diqqat", "Iltimos, avval guruhni tanlang!")
            return

        matn = self.sms_template.text.strip()
        if not matn:
            self.show_popup("Diqqat", "SMS matnini kiriting!")
            return

        try:
            interval = int(self.interval_input.text)
        except:
            interval = 5

        self.sending_queue = self.contacts[guruh]
        self.current_index = 0
        self.success_count = 0
        self.fail_count = 0
        self.current_group = guruh
        self.log_entries = []
        
        self.btn_send.disabled = True
        self.status_label.text = f"Boshlanmoqda... 0/{len(self.sending_queue)}"
        
        # Start Clock
        Clock.schedule_interval(self.send_next_sms, interval)

    def send_next_sms(self, dt):
        if self.current_index >= len(self.sending_queue):
            self.finish_sending()
            return False # Stop Clock

        number = self.sending_queue[self.current_index]
        message = self.sms_template.text
        
        try:
            sms_manager = SmsManager.getDefault()
            
            if platform == 'android':
                # Handle long messages by splitting them using Android's logic
                parts = sms_manager.divideMessage(message)
                if parts.size() > 1:
                    sms_manager.sendMultipartTextMessage(number, None, parts, None, None)
                else:
                    sms_manager.sendTextMessage(number, None, message, None, None)
            else:
                # PC Mock logic
                sms_manager.sendTextMessage(number, None, message, None, None)
            
            status = "MUVAFFAQIYATLI"
            self.success_count += 1
        except Exception as e:
            print(f"SMS xatolik: {str(e)}")
            status = f"XATOLIK ({str(e)})"
            self.fail_count += 1

        # Log entry
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_entries.append(f"{self.current_group} | {now} | {number} | {status}")
        
        self.current_index += 1
        self.status_label.text = f"Yuborilmoqda {self.current_index}/{len(self.sending_queue)}: {number}"
        
        return True # Continue Clock

    def finish_sending(self):
        self.btn_send.disabled = False
        self.status_label.text = "Tamomlandi"
        
        # Save log file
        self.save_log()
        
        # Show Summary
        summary = (
            f"Guruh: {self.current_group}\n"
            f"Umumiy: {len(self.sending_queue)}\n"
            f"Muvaffaqiyatli: {self.success_count}\n"
            f"Xatoliklar: {self.fail_count}\n\n"
            f"Hisobot saqlandi: /sdcard/sms_hisobot.txt"
        )
        self.show_popup("Yuborish yakunlandi", summary)

    def save_log(self):
        log_path = "/sdcard/sms_hisobot.txt"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n--- YANGI YUBORISH SEANSI ---\n")
                for entry in self.log_entries:
                    f.write(entry + "\n")
        except Exception as e:
            print(f"Log saqlashda xato: {e}")

    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=10)
        content.add_widget(Label(text=message, halign='center', valign='middle'))
        close_btn = Button(text="Yopish", size_hint_y=None, height=50)
        content.add_widget(close_btn)
        
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    BulkSmsApp().run()
