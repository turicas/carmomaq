#!/usr/bin/env python3

import shlex
import subprocess
from pathlib import Path


base_path = Path(__file__).parent
roast_number = input("Digite o número da torra que vamos iniciar: ").strip()
if " " in roast_number:
    print("ERRO: apenas letras e números são permitidos no número da torra.")
    input()
    exit(1)
max_time = 35
default_setup_filename = "data/setup.xls"
setup_filename = (
    input(
        f"Digite o caminho do arquivo de setup (em branco para {default_setup_filename}): "
    ).strip()
    or default_setup_filename
)
if Path(setup_filename).exists():
    print(f"ERRO: arquivo não encontrado. O arquivo deve estar em {base_path}")
    input()
    exit(2)
auto = input(
    "Você deseja que a torra seja controlada pelo programa ou você gostaria de controlá-la? Digite Y para 'sim' e N para 'não': (Y/N) "
).strip()
if auto.lower() not in ("y", "n"):
    print("ERRO: você deve digitar Y ou N.")
    input()
    exit(3)
extra_options = " --redis"
if auto:
    extra_options += " --auto"
command = (
    f"python3 torrador.py {extra_options} {roast_number} {max_time} {setup_filename}"
)

print("Ok, rodando programa torrador:")
print(f"    {command}")
print("Para sair aperte Ctrl+c (NÃO FECHE ESSA JANELA)")
print()
subprocess.Popen(shlex.split("docker-compose -f docker-compose.yml -p carmomaq up -d"), cwd=base_path)
subprocess.Popen(shlex.split(command), cwd=base_path)
input()
