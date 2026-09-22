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

"attendancemode" peut être simplifié en 1: sur place, 2: en ligne, 3: mixte, lisible directement par l'"id" contenu dans attendancemode par défaut.
    on choisit de mettre 1 par défaut si c'est null ou mal formé