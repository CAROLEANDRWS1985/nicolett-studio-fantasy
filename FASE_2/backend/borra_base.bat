del .\db.sqlite3
rmdir .\backend\__pycache__ /s /q
rmdir .\ventas\__pycache__ /s /q
rmdir .\ventas\migrations\__pycache__ /s /q
rmdir .\ventas\migrations\__pycache__ /s /q
del .\ventas\migrations\*.py /s

python manage.py makemigrations ventas 
python manage.py migrate
rem python manage.py migrate --fake

rem python manage.py createsuperuser  --username harrys  --email harrys@email.com