from django.urls import reverse_lazy
from django.views.generic import FormView

from .models import Setting
from .form import ControllerForm

from django.http import HttpResponse

from coursera_house.settings import SMART_HOME_ACCESS_TOKEN, SMART_HOME_API_URL

import requests
import json


class ControllerView(FormView):
    form_class = ControllerForm
    template_name = 'core/control.html'
    success_url = reverse_lazy('form')

    def get_context_data(self, **kwargs):
        context = super(ControllerView, self).get_context_data()
        try:
            response = requests.get(SMART_HOME_API_URL, headers={"Authorization": "Bearer " + SMART_HOME_ACCESS_TOKEN})
        except requests.HTTPError as e:
            return HttpResponse(e)
        except requests.RequestException as e:
            return HttpResponse(e)

        data = response.json()["data"]
        context['data'] = {item["name"]: item["value"] for item in data}
        context['data']['bedroom_target_temperature'] = Setting.objects.get(
            controller_name="bedroom_target_temperature").value
        context['data']['hot_water_target_temperature'] = Setting.objects.get(
            controller_name="hot_water_target_temperature").value
        return context

    def get_initial(self):
        return {}

    def form_valid(self, form):
        bedroom_target_temperature = Setting.objects.get(controller_name="bedroom_target_temperature")
        bedroom_target_temperature.value = form.cleaned_data["bedroom_target_temperature"]
        bedroom_target_temperature.save()

        hot_water_target_temperature = Setting.objects.get(controller_name="hot_water_target_temperature")
        hot_water_target_temperature.value = form.cleaned_data["hot_water_target_temperature"]
        hot_water_target_temperature.save()

        bedroom_light = form.cleaned_data["bedroom_light"]
        bathroom_light = form.cleaned_data["bathroom_light"]
        data = {"controllers": [
            {
                "name": "bedroom_light",
                "value": bedroom_light
            },
            {
                "name": "bathroom_light",
                "value": bathroom_light
            }
        ]}
        try:
            response = requests.get(SMART_HOME_API_URL, headers={"Authorization": "Bearer " + SMART_HOME_ACCESS_TOKEN})
        except requests.HTTPError as e:
            return HttpResponse(e)
        except requests.RequestException as e:
            return HttpResponse(e)

        resp_data = {contr["name"]: contr["value"] for contr in response.json()['data']
                     if contr["name"] == "bedroom_light" or contr["name"] == "bathroom_light" or contr["name"] == "smoke_detector"}
        if resp_data['bedroom_light'] != bedroom_light or resp_data['bathroom_light'] != bathroom_light:
            if resp_data['smoke_detector'] and not bedroom_light or resp_data['smoke_detector'] and not bathroom_light or not resp_data['smoke_detector']:
                r = requests.post(SMART_HOME_API_URL, data=json.dumps(data),
                                  headers={"Authorization": "Bearer " + SMART_HOME_ACCESS_TOKEN})

        return super(ControllerView, self).form_valid(form)


