"""
Pydantic request and response models, one module per resource group.

    account.py    users, tier changes
    auth.py       sign-in, tokens, the /auth/me profile
    client.py     Klien, enrolment
    common.py     shapes shared by more than one resource
    finance.py    expenses, commissions, payouts
    program.py    Harga & Program
    report.py     monthly reports, the client portal card
    schedule.py   Jadwal Klien, Jadwal Coach, schedule requests
    support.py    tickets, chat, attendance, corrections, athlete rows

Nothing is re-exported here. Endpoints import from the specific module
(`from ...schemas.common import Ok`), so adding a schema touches one file and
one import line instead of a shared barrel that has to be kept in step by hand.
A barrel that silently lags behind its modules is worse than no barrel.
"""