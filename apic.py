from dashie_sampler import DashieSampler

import requests, json, time, collections, random


class ApicConn:
    apic_ip = '10.126.216.230'
    apic_uname = 'admin'
    apic_passw = 'nbv_12345'
    mo = ''
    modata = ''
    base_url = 'http://%s/api/' % apic_ip
    inbounddata = {}

    connected = False
    auth_token = ''
    cookies = {}

    def __init__(self):
        credentials = {'aaaUser': {'attributes': {'name': self.apic_uname, 'pwd': self.apic_passw}}}
        json_credentials = json.dumps(credentials)
        login_url = self.base_url + 'aaaLogin.json'
        try:
            post_response = requests.post(login_url, data=json_credentials)
            auth = json.loads(post_response.text)
            login_attributes = auth['imdata'][0]['aaaLogin']['attributes']
            auth_token = login_attributes['token']

            self.cookies['APIC-Cookie'] = auth_token
            self.connected = True

            # example: ['imdata'][0]['eqptTempHist5min']['attributes']['currentAvg']
        except Exception,e:
            print "Exception on APIC pull: %s "% e
            self.connected = False

    def getmo(self, mo):
        sensor_url = self.base_url + mo

        try:
            get_response = requests.get(sensor_url, cookies=self.cookies, verify=False)
            self.inbounddata = get_response.json()
        except Exception, e:
            print "Exception on APIC pull: %s "% e

        return self.inbounddata


class CliConn:
    apic_uname = 'admin'
    apic_passw = 'nbv_12345'
    mo = ''
    modata = ''
    inbounddata = {}

    connected = False
    auth_token = ''
    cookies = {}

    def __init__(self,node_ip):
        # credentials = {'aaaUser': {'attributes': {'name': self.apic_uname, 'pwd': self.apic_passw}}}
        # json_credentials = json.dumps(credentials)
        # login_url = self.base_url + 'aaaLogin.json'
        self.connected = True
        self.node_ip = node_ip
        self.base_url = 'http://%s/ins/' % self.node_ip
        return

    def getmo(self, mo):
        sensor_url = self.base_url
        url=self.base_url
        switchuser=self.apic_uname
        switchpassword=self.apic_passw

        myheaders={'content-type':'application/json-rpc'}
        payload=[
          {
            "jsonrpc": "2.0",
            "method": "cli",
            "params": {
              "cmd": mo ,
              "version": 1.2
            },
            "id": 1
          }
        ]
        try:
            response = requests.post(url,data=json.dumps(payload), headers=myheaders,auth=(switchuser,switchpassword)).json()
            self.inbounddata = response
        except Exception, e:
            print "Exception on APIC pull: %s "% e

        return self.inbounddata

class CliCPU(DashieSampler):
    def __init__(self, app, interval, node_ip, ret_label, os_type):
        DashieSampler.__init__(self, app, interval)
        self._last = 0
        self.node_ip = node_ip
        self.ret_label = ret_label
        self.os_type = os_type

    def name(self):
        return self.ret_label

    def sample(self):
        sensor_url = 'show processes cpu'
        apic_conn = CliConn(self.node_ip)
        s = {'value': 0}

        if apic_conn.connected:
            try:
                data = apic_conn.getmo(sensor_url)
                if self.os_type == 1:
                    sensor_value = data['result']['body']['user_percent']
                else:
                    sensor_value = data['result']['body']['fivesec_percent']
                s = {'value': sensor_value}
            except Exception, e:
                print "Exception on CliCPU request: %s "% e
        else:
            s = {'value': 0}
        return s

class CliIP(DashieSampler):
    def __init__(self, app, interval, node_ip, ret_label, os_type):
        DashieSampler.__init__(self, app, interval)
        self._last = 0
        self.node_ip = node_ip
        self.ret_label = ret_label
        self.os_type = os_type

    def name(self):
        return self.ret_label

    def sample(self):
        sensor_url = 'show ip interface brief'
        apic_conn = CliConn(self.node_ip)
        items=[]
        s = {'items': items}
        if apic_conn.connected:
            try:
                data = apic_conn.getmo(sensor_url)
                full_list = data['result']['body']['TABLE_intf']
                for one_ip in full_list:
                    items.append({'value' : one_ip['ROW_intf']['prefix'], 'label' : one_ip['ROW_intf']['intf-name']})                
                s = {'items': items}
            except Exception, e:
                print "Exception on CliIP request: %s "% e
        else:
            s = {'items': items}
        return s

