# -*- coding: utf-8 -*-
"""
Задание 5.3a

Дополнить скрипт из задания 5.3 таким образом, чтобы, в зависимости
от выбранного режима, задавались разные вопросы в запросе о номере
VLANа или списка VLANов:
* для access: 'Введите номер VLAN:'
* для trunk: 'Введите разрешенные VLANы:'

Ограничение: Все задания надо выполнять используя только пройденные темы.
То есть эту задачу можно решить без использования условия if и циклов for/while.
"""

template = {
    "access_template": [
        "switchport mode access", "switchport access vlan {}",
        "switchport nonegotiate", "spanning-tree portfast",
        "spanning-tree bpduguard enable"
    ],

    "trunk_template": [
        "switchport trunk encapsulation dot1q", "switchport mode trunk",
        "switchport trunk allowed vlan {}"
    ]
}
quest = {
    "access" : "Введите номер VLAN: ",
    "trunk" : "Введите разрешенные VLANы: "
}

name_interface = input("Введите режим работы интерфейса (access/trunk): ")
id_interface = input("Введите тип и номер интерфейса: ")
vlans = input(quest[name_interface])

print("interface " + id_interface)
print("\n".join(template[name_interface + "_template"]).format(vlans))