import datetime
from datetime import datetime, timedelta

#preprocess 1: calculate response time
df_join['submission'] = pd.to_datetime(df_join['submission'], format='%Y-%m-%d %H:%M:%S')
df_join['response'] = pd.to_datetime(df_join['response'], format='%Y-%m-%d %H:%M:%S')

df_join['approval_time'] = df_join['response']-df_join['submission']
df_join['approval_hours'] = df_join['approval_time'].dt.total_seconds() / 3600
df_join['approval_minutes'] = df_join['approval_time'].dt.total_seconds() / 60

#preprocess 2: time of submission
df_join['year'] = df_join['submission'].dt.year
df_join['quarter'] = df_join['submission'].dt.to_period('Q')
df_join['month'] = df_join['submission'].dt.month
df_join['date'] = df_join['submission'].dt.date
df_join['day'] = df_join['submission'].dt.day_name()
df_join['hour'] = df_join['submission'].dt.hour


#subset data out of scope
df_join = df_join[df_join['year'] != 2023]
df_join = df_join[df_join['year'] != 2024]
df_join = df_join[df_join['year'] != 2026]

#Checking bug
df_join_bug=df_join[df_join['approval_time']<timedelta(seconds=0)]
df_join_bug.head()

#df_join_bug.to_excel('data_bug.xlsx', index=False)
