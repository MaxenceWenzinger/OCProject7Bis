# Les données

1135178 entrées en base entre le 2016,1,1 et 2028,1,1, download le 2026,9,21  
1065411 restantes après filtre country_fr = France (Métropole)  
1062251 restantes avec description not null  
1062249 restantes avec title_fr not null  
1039252 restantes en supprimant les doublons ["title_fr", "firstdate_begin", "location_name", "description_fr", "longdescription_fr"]  
1028694 restantes avec des "timings" logiques

"accessibility" et "accessibility_label_fr" contiennent les mêmes infos, mais en mots entiers ou en abbréviation.  
    pi psychical impairment  
    hi hearing impairment  
    mi motor impairment  
    vi visual impairment  
    ii intellectual impairment

"attendancemode" peut être simplifié en 1: sur place, 2: en ligne, 3: mixte, lisible directement par l'"id" contenu dans attendancemode par défaut.  
    on choisit de mettre 1 par défaut si c'est null ou mal formé

Après relecture de l'énoncé, filtrage sur environ 1 an avant à 1 an après, du coup:  
263628 entrées de base  
250676 en france  
250238 description non null  
250238 title non null  
244922 sans doublons  
244922 après check des timings

# Stockage en bdd

Installer pgvector pour PostgreSQL  
https://github.com/pgvector/pgvector#installation-notes---windows

Compatibilité python  
https://github.com/pgvector/pgvector-python

Configurer le .env.

'''
uv run alembic upgrade head
'''

# Vectorisation

Tests de rapidité de la vectorisation bge-m3 avec batches de 32 (les documents de ce test sont titre\ndescription):  
0.03s par entrée en passant par ollama, mais résultats denses uniquement  
0.056s en passant par FlagEmbedding, mais on a accès à sparse et colbert si on veut  
Augmenter la taille des batches n'a pas d'effet positif visible.  
Réduire la taille à 8-16 semble étonnament améliorer l'efficacité de FlagEmbedding qui descend à 0.04s

Taille maximum des documents sous le format titre\nmots_clefs\nlieu\ndescription\nlongdescription: 10181 caractères, bien en-dessous du max de bge-m3  
Donc en première approche, 1 chunk = 1 document  
A 1 chunk par document, on produit les embedding à environ 1 par 0.2s  
Mise en place d'un système de découpe des documents en chunks plus petits avec recouvrement pour potentiellement respecter des conseils disant qu'un chunk devrait être entre 512 et 1024 tokens avec 10-20% de recouvrement.  
Pour bge-m3 1 token = 3.25 caractères français.  
Le build de l'index total serait donc estimé à 12 heures. Mise en place d'un système pour ne pas perdre tout le travail en cas de plantage.