#data collection - web scrapping
import requests
import pandas as pd
from io import StringIO

#list of port
port_code = ['IDAGS','IDAHI','IDAMQ','IDAPN','IDTZD','IDAGK','IDAAU','IDBRO','IDLBH','IDPBB',
             'IDBXD','IDBII','IDBAE','IDBAI','IDBPN','IDNDA','IDBGG','IDBDJ','IDBTN','IDBJU',
             'IDBAA','IDBRS','IDBTX','IDBTM','IDBTG','IDBAU','IDBWN','IDBBM','IDBLW','IDBEN',
             'IDBKI','IDBKS','IDBOA','IDBIK','IDBMU','IDLBI','IDNTI','IDBIT','IDBXT','IDSNP',
             'IDBNQ','IDBUA','IDBUI','IDBBE','IDBNU','IDBUD','IDBYQ','IDCLI','IDCLG','IDCEB',
             'IDCXP','IDCBN','IDDAS','IDDAR','IDDOB','IDDUM','IDENE','IDFKQ','IDGNG','IDGER',
             'IDCXP','IDCBN','IDDAS','IDDAR','IDDOB','IDDUM','IDENE','IDFKQ','IDGNG','IDGER',
             'IDGIL','IDGTO','IDGRE','IDGNS','IDHUU','IDIRU','IDJIO','IDDJJ','IDJEO','IDJEP',
             'IDJWA','IDKNG','IDKBH','IDKAT','IDKNU','IDKJA','XXOGA','PUSAT','IDKDI','IDKDW',
             'IDKSB','IDKTG','IDKID','IDKNP','IDKKS','IDKOL','IDKNL','IDKRO','IDKAG','IDKBU',
             'IDKAN','IDRGT','IDENO','IDKGQ','IDKUA','IDKME','IDKSA','IDKTK','IDKTJ','IDKUM',
             'IDKOE','IDKWG','IDLBO','IDLAJ','IDLLO','IDLMA','IDLUK','IDLHA','IDLII','IDLPO',
             'IDLKA','IDLBR','IDLEK','IDLWE','IDLSW','IDLUG','IDLUW','IDMII','IDMAJ','IDMAK',
             'IDMLH','IDMKI','IDMLI','IDMJU','IDMDC','IDMGA','IDMAN','IDMKW','IDMOT','IDMRA',
             'IDMSI','IDMOF','IDMGE','IDMKQ','IDMSJ','IDMEQ','IDMLW','IDMKA','IDMSK','IDMSB',
             'IDMUO','IDNBX','IDNAM','IDNRE','IDNIJ','IDNNX','IDNPE','IDOOS','IDORA','IDPBI',
             'IDPTA','IDPGM','IDPLM','IDPAH','IDPPO','IDPRN','IDPAN','IDPGX','IDPKN','IDPKS',
             'IDPIN','IDPNJ','IDPAP','IDPRI','IDPMB','IDPIO','IDPKU','IDPRA','IDMEN','IDPMK',
             'IDPUM','IDPNK','IDPSJ','IDPRO','IDPPS','IDPJA','IDPTE','IDRAQ','IDRGG','IDREM',
             'IDREO','IDSBG','IDSDI','IDSKT','IDSRI','IDSMQ','IDSQN','IDSGQ','IDSKI','IDSPE',
             'IDSPN','IDSPI','IDZRM','IDSTU','IDSXK','IDSEA','IDSPA','IDSLR','IDSAG','IDZRI',
             'IDSLG','IDSIK','IDSNG','IDSNL','IDSLA','IDSNE','IDSRU','IDSON','IDSWA','IDSIO',
             'IDSFI','IDSOQ','IDSAA','IDSKL','IDSUQ','IDSLU','IDSNY','IDSSL','IDSUS','IDTHA',
             'IDDJB','IDTHR','IDTSH','IDTJB','IDTBE','IDBUT','IDSRG','IDTMD','IDTJQ','IDSUB',
             'IDTNJ','IDJKT','IDTRE','IDTSX','IDTJS','IDPEI','IDTAN','IDTPK','IDTRK','IDTMP',
             'IDTEG','IDTGU','IDTMO','IDTBR','IDTDA','IDLIG','IDPTL','IDTTN','IDTLN','IDTXM',
             'IDTTE','IDSEL','IDTAA','IDTBO','IDTLI','IDTUA','IDTLU','IDUSI','IDWIO','IDWGP',
             'IDWSA','IDWCI','IDWRN','IDWSR','IDWED','IDWII','IDWNI']

#type of service, dn = domestic, ln = overseas
angkutan = ['dn', 'ln']
hasil = []

#scrapping 1: obtaining pkk dataset
for service in angkutan:
    for port in port_code:
        for Month in range(1,13):
            url = f"https://monitoring-inaportnet.dephub.go.id/monitoring/byPort/list/{port}/{service}/2025/{Month:02d}"
            print(url)
            r = requests.get(url)
            if r.status_code != 200:
                print("Gagal")
                continue
            js = r.json()
            if len(js["data"]) == 0:
                continue
            df = pd.DataFrame(js["data"])
            df["bulan"] = Month
            df["pelabuhan"] = port
            hasil.append(df)
            
df_all = pd.concat(hasil, ignore_index=True)
df_pkk = df_all[
  ["nomor_pkk", "nama_kapal", "pelabuhan_kode", "bulan"]
].copy()


#scrapping 2: obtaining approval/response time
approval_list = []
for nomor_pkk in df_pkk["nomor_pkk"]:
    url = f"https://monitoring-inaportnet.dephub.go.id/monitoring/detail?nomor_pkk={nomor_pkk}"
    try:
        html = requests.get(url, timeout=30).text
        dfs = pd.read_html(StringIO(html))
        approval = dfs[2].copy()
        approval.columns = approval.columns.get_level_values(1)
        approval = approval[approval["Layanan"] == "PKK"]
        approval = approval[
            ["Layanan",
             "Permohonan",
             "Persetujuan",
             "Nomor Produk"]
        ]
        approval["nomor_pkk"] = nomor_pkk
        approval_list.append(approval)
    except Exception as e:
        print(f"Gagal membaca {nomor_pkk} : {e}")

approval_df = pd.concat(approval_list, ignore_index=True)

#merging dataset of list of pkk (df_pkk) with approval
df_pkk = df_pkk.merge(
    approval_df,
    on="nomor_pkk",
    how="left"
)
df_pkk.head()

#import code of inaport to define port name
df_port = pd.read_excel('port_code.xlsx') #carefull on the file location


#merging/joining dataset (port name and approval dataset)
df_join = df_pkk.merge(df_port, left_on='pelabuhan_kode', right_on='KODE', how='inner')

#column list expected
rename_cols = {
    "pelabuhan_kode": "port_code",
    "PELABUHAN": "port",
    "nomor_pkk": "PKK_number",
    "nama_kapal": "vessel_name",
    "Layanan": "service",
    "Permohonan": "submission",
    "Persetujuan": "response",
    "Nomor Produk": "simpadu",
    "GMT": "GMT"
}

#rename columns and sort as expected
df_join = df_join.rename(columns=rename_cols)[
    [
        "port_code",
        "port",
        "PKK_number", 
        "vessel_name", 
        "service", 
        "submission", 
        "response", 
        "simpadu",
        "GMT"
    ]
]

df_join.head()


