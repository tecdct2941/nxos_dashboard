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

           #  print "loggerd in"
            # example: ['imdata'][0]['eqptTempHist5min']['attributes']['currentAvg']
          #  exit()
        except Exception,e:
            print "Exception on APIC pull: %s ", e
            self.connected = False

    def getmo(self, mo):
        sensor_url = self.base_url + mo

        try:
            get_response = requests.get(sensor_url, cookies=self.cookies, verify=False)
            self.inbounddata = get_response.json()
        except Exception, e:
            print "Exception on APIC pull: %s ", e

        return self.inbounddata


class ApicTemp(DashieSampler):
    def __init__(self, *args, **kwargs):
        DashieSampler.__init__(self, *args, **kwargs)
        self._last = 0

    def name(self):
        return 'apic_temp'

    def sample(self):
        sensor_url = 'mo/topology/pod-1/node-202/sys/ch/supslot-1/sup/sensor-3/HDeqptTemp5min-0.json'
        apic_conn = ApicConn()

        if apic_conn.connected:
            data = apic_conn.getmo(sensor_url)
            sensor_value = data['imdata'][0]['eqptTempHist5min']['attributes']['currentAvg']
            s = {'text': str(sensor_value)}
        else:
            s = {'text': 'No Data from APIC'}

        return s


class ApicHealth(DashieSampler):
    def __init__(self, *args, **kwargs):
        DashieSampler.__init__(self, *args, **kwargs)
        self._last = 0

    def name(self):
        return 'apic_health'

    def sample(self):
        sensor_url = 'mo/topology/HDfabricOverallHealth5min-0.json'
        apic_conn = ApicConn()

        if apic_conn.connected:
            data = apic_conn.getmo(sensor_url)
            sensor_value = data['imdata'][0]['fabricOverallHealthHist5min']['attributes']['healthAvg']
            s = {'text': str(sensor_value)}
        else:
            s = {'text': 'No Data from APIC'}

        return s


class TenantHealth(DashieSampler):
    tenant = ''

    def __init__(self, app, interval, tenant):
        DashieSampler.__init__(self, app, interval)
        self._last = 0
        self.tenant = tenant

    def name(self):
        return 'tenant_health_%s' % self.tenant

    def sample(self):
        sensor_url = '/node/mo/uni/tn-%s/HDfvOverallHealth15min-0.json' % self.tenant
        apic_conn = ApicConn()

        if apic_conn.connected:
            data = apic_conn.getmo(sensor_url)
            avg_health = data['imdata'][0]['fvOverallHealthHist15min']['attributes']['healthAvg']
            min_health = data['imdata'][0]['fvOverallHealthHist15min']['attributes']['healthMin']
            max_health = data['imdata'][0]['fvOverallHealthHist15min']['attributes']['healthMax']

            items=[{'label':'15 Minute Average','value':avg_health},
                   {'label':'Minimum Health','value':min_health},
                   {'label':'Maximum Health','value':max_health}
                   ]
            s = {'items': items}
        else:
            items=[{'label':'Data', 'value':'ERROR'}]
            s = {'items': items}
        return s


class NetworkEndpoints(DashieSampler):
    def __init__(self, *args, **kwargs ):
        DashieSampler.__init__(self, *args, **kwargs)
        self._last = 0

    def name(self):
        return 'epg_endpoints'


class NetworkEndpointsCount(DashieSampler):
    tenant = ''
    epg = ''
    anp = ''
    netmax = 254

    def __init__(self, app, interval, tenant, anp, epg, netmax):
        DashieSampler.__init__(self, app, interval)
        self._last = 0
        self.tenant = tenant
        self.epg = epg
        self.anp = anp
        self.netmax = netmax

    def name(self):
        return 'network_endpoint_count_%s' % self.epg

    def sample(self):
        sensor_url = 'node/mo/uni/tn-%s/ap-%s/epg-%s.json?query-target=children' % (self.tenant, self.anp, self.epg)
        apic_conn = ApicConn()

        if apic_conn.connected:
            data = apic_conn.getmo(sensor_url)
            endpoint_count = data['totalCount']

            s = {'value': int(endpoint_count),
                 'current': int(endpoint_count),
                 'last': self._last}
            self._last = s['current']
        else:
            items = [{'label': 'Data', 'value': 'ERROR'}]
            s = {'current': 0}

        return s


class EpgStats(DashieSampler):
    tenant = ''
    epg = ''
    anp = ''

    def __init__(self, app, interval, tenant, anp, epg):
        DashieSampler.__init__(self, app, interval)
        self.items = collections.deque()
        self.seedX = 0
        self.tenant = tenant
        self.epg = epg
        self.anp = anp

    def name(self):
        return 'epg_stats_%s' % self.epg

    def sample(self):
        sensor_url = 'node/mo/uni/tn-%s/ap-%s/epg-%s.json?rsp-subtree-include=stats&rsp-subtree-class=l2IngrBytesAgHist15min' % (self.tenant, self.anp, self.epg)
        apic_conn = ApicConn()

        if apic_conn.connected:
            data = apic_conn.getmo(sensor_url)

            all_entries = []

            for l2IngrBytes in data['imdata'][0]['fvAEPg']['children']:
                linedate = l2IngrBytes['l2IngrBytesAgHist15min']['attributes']['repIntvEnd'].split('T')[0]
                linetime = l2IngrBytes['l2IngrBytesAgHist15min']['attributes']['repIntvEnd'].split('T')[1].split('-')[0].split('.')[0]

                entrytime = time.strptime('%s %s' % (linedate, linetime), '%Y-%m-%d %H:%M:%S')

                data = {
                    'unixtime': int(time.mktime(entrytime)),
                    'unicastRate': l2IngrBytes['l2IngrBytesAgHist15min']['attributes']['unicastPer'].split('.')[0],
                    'multicastRate': l2IngrBytes['l2IngrBytesAgHist15min']['attributes']['multicastRate'].split('.')[0],
                    'repIntvStart': l2IngrBytes['l2IngrBytesAgHist15min']['attributes']['repIntvStart'],
                }
                all_entries.append(data)

            ordered_list = sorted(all_entries, key=lambda k: k['unixtime'])
            dashie_list = collections.deque()

            self.seedX = 0
            for row in ordered_list:
                dashie_list.append({
                    'x': self.seedX,
                    'y': int(row['unicastRate'])
                })
                self.seedX += 1
                if len(dashie_list) > 60:
                    dashie_list.popleft()

            s = {'points': list(dashie_list)}
        else:
            s = {'points': 0}

        return s


class EpgStatsFake(DashieSampler):
    def name(self):
        return 'epg_stats_fake'

    def __init__(self, *args, **kwargs):
        self.seedX = 0
        self.items = collections.deque()
        DashieSampler.__init__(self, *args, **kwargs)

    def sample(self):
        self.items.append({'x': self.seedX,
                           'y': random.randint(150000, 800000)})
        self.seedX += 1
        if len(self.items) > 60:
            self.items.popleft()

        return {'points': list(self.items)}

class EpgEndPointsFake(DashieSampler):
    def __init__(self, *args, **kwargs):
        DashieSampler.__init__(self, *args, **kwargs)
        self._last = 0

    def name(self):
        return 'endpointfakedata'

    def sample(self):
        s = {'value': random.randint(240, 250),
             'current': random.randint(240, 250),
             'last': self._last}
        self._last = s['current']
        return s



class FabricMembersHealth(DashieSampler):
    tenant = ''
    epg = ''
    anp = ''

    def __init__(self, app, interval ):
        DashieSampler.__init__(self, app, interval)

    def name(self):
        return 'fabric_members_health'

    def sample(self):
        sensor_url = 'node/class/topSystem.json?rsp-subtree-include=health'
        apic_conn = ApicConn()

        if apic_conn.connected:
            data = apic_conn.getmo(sensor_url)

            items = []

            for topSystem in data['imdata']:
                if (topSystem['topSystem']['attributes']['role'] == "leaf") or (topSystem['topSystem']['attributes']['role'] == "spine"):
                    label_string = "%s %s" % ( topSystem['topSystem']['attributes']['role'], topSystem['topSystem']['attributes']['id'])
                    value_string = "%s" % topSystem['topSystem']['children'][0]['healthInst']['attributes']['cur']

                    items.append({'label': label_string, 'value': value_string})

            s = {'items': items}
        else:
            s = {'items': 0}

        return s


class AllTenants(DashieSampler):
    tenant = ''
    epg = ''
    anp = ''

    def __init__(self, app, interval ):
        DashieSampler.__init__(self, app, interval)

    def name(self):
        return 'all_tenants'

    def sample(self):
        sensor_url = 'node/class/fvTenant.json?rsp-subtree-include=health,required'
        apic_conn = ApicConn()

        if apic_conn.connected:
            data = apic_conn.getmo(sensor_url)
            items = []
            for tenant in data['imdata']:
                label_string = "%s" % tenant['fvTenant']['attributes']['name']
                value_string = "%s" % tenant['fvTenant']['children'][0]['healthInst']['attributes']['cur']
                items.append({'label': label_string, 'value': value_string})

            s = {'items': items}
        else:
            s = {'items': 0}

        return s


