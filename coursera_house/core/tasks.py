from __future__ import absolute_import, unicode_literals
from celery import task
import requests
import json
from coursera_house.settings import SMART_HOME_ACCESS_TOKEN, SMART_HOME_API_URL, EMAIL_RECEPIENT
from django.core.mail import EmailMessage

from .models import Setting
from django.http import HttpResponse


@task()
def smart_home_manager():
    # Здесь ваш код для проверки условий
    send_letter = False
    response = requests.get(SMART_HOME_API_URL, headers={"Authorization": "Bearer " + SMART_HOME_ACCESS_TOKEN})

    data = response.json()['data']
    controllers = {}
    for controller in data:
        controllers[controller['name']] = {key: value for key, value in controller.items()}

    hot_water_target_temperature = Setting.objects.get(controller_name="hot_water_target_temperature").value
    bedroom_target_temperature = Setting.objects.get(controller_name="bedroom_target_temperature").value

    #hot_water_target_temperature = 90
    #bedroom_target_temperature = 21

    def turn_on_boiler():
        if controllers['cold_water']['value'] and not controllers['smoke_detector']['value']:
            if not controllers['boiler']['value']:
                controllers['boiler']['value'] = True
                write_contr.add('boiler')

    def turn_on_washing_machine():
        if controllers['cold_water']['value'] and not controllers['smoke_detector']['value']:
            if controllers['washing_machine']['value'] == 'off':
                controllers['washing_machine']['value'] = 'on'
                write_contr.add('washing_machine')

    def change_curtains(status):
        if controllers['curtains']['value'] != 'slightly_open':
            if controllers['curtains']['value'] != status:
                controllers['curtains']['value'] = status
                write_contr.add('curtains')

    def turn_on_air_conditioner():
        if not controllers['smoke_detector']['value']:
            if not controllers['air_conditioner']['value']:
                controllers['air_conditioner']['value'] = True
                write_contr.add('air_conditioner')


    write_contr = set()

    for i in range(10):
            # 1
        if controllers['leak_detector']['value']:

            if controllers['cold_water']['value']:
                controllers['cold_water']['value'] = False
                write_contr.add('cold_water')

            if controllers['hot_water']['value']:
                controllers['hot_water']['value'] = False
                write_contr.add('hot_water')
            send_letter = True

        # 2
        if not controllers['cold_water']['value']:
            if controllers['boiler']['value']:
                controllers['boiler']['value'] = False
                write_contr.add('boiler')
            if controllers['washing_machine']['value'] != 'off':
                controllers['washing_machine']['value'] = 'off'
                write_contr.add('washing_machine')

        # 3
        if (controllers['boiler_temperature']['value'] and
                controllers['boiler_temperature']['value'] < 0.9 * hot_water_target_temperature):
            turn_on_boiler()

        if (controllers['boiler_temperature']['value'] and
                controllers['boiler_temperature']['value'] >= 1.1 * hot_water_target_temperature):
            if controllers['boiler']['value']:
                controllers['boiler']['value'] = False
                write_contr.add('boiler')
        elif controllers['boiler_temperature']['value'] and controllers['boiler_temperature']['value'] >= 90:
            if controllers['boiler']['value']:
                controllers['boiler']['value'] = False
                write_contr.add('boiler')

        # 5
        if (controllers['outdoor_light']['value'] < 50 and
                not controllers['bedroom_light']['value']):
            change_curtains('open')

        if (controllers['outdoor_light']['value'] >= 50 or
              controllers['bedroom_light']['value']):
            change_curtains('close')

        # 6

        if controllers['smoke_detector']['value']:
            for item in 'air_conditioner', 'bedroom_light', 'bathroom_light', 'boiler', 'washing_machine':
                if item == 'washing_machine':
                    if controllers[item]['value'] == 'on':
                        controllers[item]['value'] = 'off'
                        write_contr.add(item)
                    continue
                if controllers[item]['value']:
                    controllers[item]['value'] = False
                    write_contr.add(item)

        # 7

        if controllers['bedroom_temperature']['value'] >= 1.1 * bedroom_target_temperature:
            turn_on_air_conditioner()

        if controllers['bedroom_temperature']['value'] < 0.9 * bedroom_target_temperature\
                or controllers['bedroom_temperature']['value'] <= 16:
            if controllers['air_conditioner']['value']:
                controllers['air_conditioner']['value'] = False
                write_contr.add('air_conditioner')

    data = {"controllers": [
        {"name": name, "value": controllers[name]["value"]}
        for name in write_contr
    ]}
    requests.post(SMART_HOME_API_URL, data=json.dumps(data),
                        headers={"Authorization": "Bearer " + SMART_HOME_ACCESS_TOKEN})
    if send_letter:
        email = EmailMessage('title', 'body', to=[EMAIL_RECEPIENT])
        email.send()
        # send_mail("ALARM!",
        #          "YOUR WATER IS GOING OUT!",
        #          'gardiys0213@yandex.ru',
        #          [EMAIL_RECEPIENT])

#smart_home_manager()