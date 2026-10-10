"""Synthetic browser verification data; refuses the real-data database."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from hashlib import sha256
from pydantic import SecretStr
from p50k.product.auth import hash_password
from p50k.product.ai_client import AIConfig
from p50k.product.db import connect
from p50k.product.decisions import evaluate
from p50k.product.detector_runner import run
from p50k.product.settings import Settings

EMAIL='synthetic-browser@example.invalid'
PASSWORD='synthetic-browser-password'

def main():
    settings=Settings.from_env()
    if settings.db_name!='p50k_dev' or settings.db_user!='p50k_owner':
        raise RuntimeError('Smoke seed requires owner access to p50k_dev')
    with connect(settings) as connection:
        connection.execute("INSERT INTO auth.users(email,password_hash,role) VALUES (%s,%s,'admin') ON CONFLICT(email) DO UPDATE SET password_hash=EXCLUDED.password_hash,disabled_at=NULL",
            (EMAIL,hash_password(SecretStr(PASSWORD),settings.auth_pepper())))
        checksum=sha256(b'synthetic-browser-seed-v2').hexdigest()
        connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES ('THF','Synthetic browser fund','Synthetic category',%s) ON CONFLICT DO NOTHING",(checksum,))
        for index in range(10):
            day=(datetime.now(timezone.utc)-timedelta(days=10-index)).date()
            available=datetime.combine(day,datetime.min.time(),timezone.utc)
            connection.execute("INSERT INTO obs.fund_prices(fund_code,effective_date,nav,source_sha256,origin,available_at,observed_at,availability_rule) VALUES ('THF',%s,%s,%s,'SYNTHETIC',%s,%s,'synthetic-browser') ON CONFLICT DO NOTHING",
                (day,Decimal(100+index) if index not in {4,9} else None,checksum,available,available))
    app=replace(settings,db_user='p50k_app',db_password_file=__import__('pathlib').Path('/run/secrets/db_app_password'))
    with connect(app) as connection:
        run(connection,datetime.now(timezone.utc),'SYNTHETIC')
    evaluate(app,'THF',AIConfig(mode='mock'))
    print('Synthetic browser seed ready; no real database touched.')

if __name__=='__main__':main()
