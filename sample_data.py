"""Fictional asking-price examples, not collected marketplace records."""


def sample_records():
    rows = [
        ('1', 'Sony WH-1000XM5', 'Sony WH-1000XM5 headphones', 320,
         'Used headphones, tested controls, includes original case and charging cable.'),
        ('2', 'Sony WH-1000XM5', 'Sony WH-1000XM5 headphones', 480,
         'Used headphones with the case and charging cable. All controls tested.'),
        ('3', 'Sony WH-1000XM4', 'Sony WH-1000XM4 headphones', 260,
         'Previous model. Used headphones with a case and cable.'),
        ('4', 'Sony WH-1000XM5 case', 'Sony WH-1000XM5 headphones carrying case', 35,
         'Carrying case only. No headphones included.'),
        ('5', 'Sony WH-1000XM5', 'Sony WH-1000XM5 headphones', 210,
         'Used headphones with missing earpads. Sold as is, no return.'),
        ('6', 'Fujifilm X100V', 'Fujifilm X100V camera', 3200,
         'Used camera. Seller states the controls and lens have been checked.'),
        ('7', 'Fujifilm X100V', 'Fujifilm X100V camera', 3800,
         'Used camera with charging cable. No photo inspection has been carried out.'),
        ('8', 'Fujifilm X100V', 'Fujifilm X100V camera', 4100,
         'Used camera with packaging. Condition needs confirmation with the seller.'),
    ]
    return [
        {'id': identity, 'product': product, 'title': title, 'price': price,
         'description': description,
         'url': f'https://www.carousell.com.my/p/synthetic-record-{identity}/',
         'marketplace': 'carousell', 'condition': 'Used'}
        for identity, product, title, price, description in rows
    ]

