# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        ('base', '0002_remove_resourcebase_contacts'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactrole',
            name='area',
            field=models.CharField(help_text='state, province of the location', max_length=255, null=True, verbose_name='Administrative Area', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='city',
            field=models.CharField(help_text='city of the location', max_length=255, null=True, verbose_name='City', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='country',
            field=models.CharField(blank=True, max_length=3, null=True, help_text='country of the physical address', choices=[(b'AFG', b'Afghanistan'), (b'ALA', b'Aland Islands'), (b'ALB', b'Albania'), (b'DZA', b'Algeria'), (b'ASM', b'American Samoa'), (b'AND', b'Andorra'), (b'AGO', b'Angola'), (b'AIA', b'Anguilla'), (b'ATG', b'Antigua and Barbuda'), (b'ARG', b'Argentina'), (b'ARM', b'Armenia'), (b'ABW', b'Aruba'), (b'AUS', b'Australia'), (b'AUT', b'Austria'), (b'AZE', b'Azerbaijan'), (b'BHS', b'Bahamas'), (b'BHR', b'Bahrain'), (b'BGD', b'Bangladesh'), (b'BRB', b'Barbados'), (b'BLR', b'Belarus'), (b'BEL', b'Belgium'), (b'BLZ', b'Belize'), (b'BEN', b'Benin'), (b'BMU', b'Bermuda'), (b'BTN', b'Bhutan'), (b'BOL', b'Bolivia'), (b'BIH', b'Bosnia and Herzegovina'), (b'BWA', b'Botswana'), (b'BRA', b'Brazil'), (b'VGB', b'British Virgin Islands'), (b'BRN', b'Brunei Darussalam'), (b'BGR', b'Bulgaria'), (b'BFA', b'Burkina Faso'), (b'BDI', b'Burundi'), (b'KHM', b'Cambodia'), (b'CMR', b'Cameroon'), (b'CAN', b'Canada'), (b'CPV', b'Cape Verde'), (b'CYM', b'Cayman Islands'), (b'CAF', b'Central African Republic'), (b'TCD', b'Chad'), (b'CIL', b'Channel Islands'), (b'CHL', b'Chile'), (b'CHN', b'China'), (b'HKG', b'China - Hong Kong'), (b'MAC', b'China - Macao'), (b'COL', b'Colombia'), (b'COM', b'Comoros'), (b'COG', b'Congo'), (b'COK', b'Cook Islands'), (b'CRI', b'Costa Rica'), (b'CIV', b"Cote d'Ivoire"), (b'HRV', b'Croatia'), (b'CUB', b'Cuba'), (b'CYP', b'Cyprus'), (b'CZE', b'Czech Republic'), (b'PRK', b"Democratic People's Republic of Korea"), (b'COD', b'Democratic Republic of the Congo'), (b'DNK', b'Denmark'), (b'DJI', b'Djibouti'), (b'DMA', b'Dominica'), (b'DOM', b'Dominican Republic'), (b'ECU', b'Ecuador'), (b'EGY', b'Egypt'), (b'SLV', b'El Salvador'), (b'GNQ', b'Equatorial Guinea'), (b'ERI', b'Eritrea'), (b'EST', b'Estonia'), (b'ETH', b'Ethiopia'), (b'FRO', b'Faeroe Islands'), (b'FLK', b'Falkland Islands (Malvinas)'), (b'FJI', b'Fiji'), (b'FIN', b'Finland'), (b'FRA', b'France'), (b'GUF', b'French Guiana'), (b'PYF', b'French Polynesia'), (b'GAB', b'Gabon'), (b'GMB', b'Gambia'), (b'GEO', b'Georgia'), (b'DEU', b'Germany'), (b'GHA', b'Ghana'), (b'GIB', b'Gibraltar'), (b'GRC', b'Greece'), (b'GRL', b'Greenland'), (b'GRD', b'Grenada'), (b'GLP', b'Guadeloupe'), (b'GUM', b'Guam'), (b'GTM', b'Guatemala'), (b'GGY', b'Guernsey'), (b'GIN', b'Guinea'), (b'GNB', b'Guinea-Bissau'), (b'GUY', b'Guyana'), (b'HTI', b'Haiti'), (b'VAT', b'Holy See (Vatican City)'), (b'HND', b'Honduras'), (b'HUN', b'Hungary'), (b'ISL', b'Iceland'), (b'IND', b'India'), (b'IDN', b'Indonesia'), (b'IRN', b'Iran'), (b'IRQ', b'Iraq'), (b'IRL', b'Ireland'), (b'IMN', b'Isle of Man'), (b'ISR', b'Israel'), (b'ITA', b'Italy'), (b'JAM', b'Jamaica'), (b'JPN', b'Japan'), (b'JEY', b'Jersey'), (b'JOR', b'Jordan'), (b'KAZ', b'Kazakhstan'), (b'KEN', b'Kenya'), (b'KIR', b'Kiribati'), (b'KWT', b'Kuwait'), (b'KGZ', b'Kyrgyzstan'), (b'LAO', b"Lao People's Democratic Republic"), (b'LVA', b'Latvia'), (b'LBN', b'Lebanon'), (b'LSO', b'Lesotho'), (b'LBR', b'Liberia'), (b'LBY', b'Libyan Arab Jamahiriya'), (b'LIE', b'Liechtenstein'), (b'LTU', b'Lithuania'), (b'LUX', b'Luxembourg'), (b'MKD', b'Macedonia'), (b'MDG', b'Madagascar'), (b'MWI', b'Malawi'), (b'MYS', b'Malaysia'), (b'MDV', b'Maldives'), (b'MLI', b'Mali'), (b'MLT', b'Malta'), (b'MHL', b'Marshall Islands'), (b'MTQ', b'Martinique'), (b'MRT', b'Mauritania'), (b'MUS', b'Mauritius'), (b'MYT', b'Mayotte'), (b'MEX', b'Mexico'), (b'FSM', b'Micronesia, Federated States of'), (b'MCO', b'Monaco'), (b'MNG', b'Mongolia'), (b'MNE', b'Montenegro'), (b'MSR', b'Montserrat'), (b'MAR', b'Morocco'), (b'MOZ', b'Mozambique'), (b'MMR', b'Myanmar'), (b'NAM', b'Namibia'), (b'NRU', b'Nauru'), (b'NPL', b'Nepal'), (b'NLD', b'Netherlands'), (b'ANT', b'Netherlands Antilles'), (b'NCL', b'New Caledonia'), (b'NZL', b'New Zealand'), (b'NIC', b'Nicaragua'), (b'NER', b'Niger'), (b'NGA', b'Nigeria'), (b'NIU', b'Niue'), (b'NFK', b'Norfolk Island'), (b'MNP', b'Northern Mariana Islands'), (b'NOR', b'Norway'), (b'PSE', b'Occupied Palestinian Territory'), (b'OMN', b'Oman'), (b'PAK', b'Pakistan'), (b'PLW', b'Palau'), (b'PAN', b'Panama'), (b'PNG', b'Papua New Guinea'), (b'PRY', b'Paraguay'), (b'PER', b'Peru'), (b'PHL', b'Philippines'), (b'PCN', b'Pitcairn'), (b'POL', b'Poland'), (b'PRT', b'Portugal'), (b'PRI', b'Puerto Rico'), (b'QAT', b'Qatar'), (b'KOR', b'Republic of Korea'), (b'MDA', b'Republic of Moldova'), (b'REU', b'Reunion'), (b'ROU', b'Romania'), (b'RUS', b'Russian Federation'), (b'RWA', b'Rwanda'), (b'BLM', b'Saint-Barthelemy'), (b'SHN', b'Saint Helena'), (b'KNA', b'Saint Kitts and Nevis'), (b'LCA', b'Saint Lucia'), (b'MAF', b'Saint-Martin (French part)'), (b'SPM', b'Saint Pierre and Miquelon'), (b'VCT', b'Saint Vincent and the Grenadines'), (b'WSM', b'Samoa'), (b'SMR', b'San Marino'), (b'STP', b'Sao Tome and Principe'), (b'SAU', b'Saudi Arabia'), (b'SEN', b'Senegal'), (b'SRB', b'Serbia'), (b'SYC', b'Seychelles'), (b'SLE', b'Sierra Leone'), (b'SGP', b'Singapore'), (b'SVK', b'Slovakia'), (b'SVN', b'Slovenia'), (b'SLB', b'Solomon Islands'), (b'SOM', b'Somalia'), (b'ZAF', b'South Africa'), (b'SSD', b'South Sudan'), (b'ESP', b'Spain'), (b'LKA', b'Sri Lanka'), (b'SDN', b'Sudan'), (b'SUR', b'Suriname'), (b'SJM', b'Svalbard and Jan Mayen Islands'), (b'SWZ', b'Swaziland'), (b'SWE', b'Sweden'), (b'CHE', b'Switzerland'), (b'SYR', b'Syrian Arab Republic'), (b'TJK', b'Tajikistan'), (b'THA', b'Thailand'), (b'TLS', b'Timor-Leste'), (b'TGO', b'Togo'), (b'TKL', b'Tokelau'), (b'TON', b'Tonga'), (b'TTO', b'Trinidad and Tobago'), (b'TUN', b'Tunisia'), (b'TUR', b'Turkey'), (b'TKM', b'Turkmenistan'), (b'TCA', b'Turks and Caicos Islands'), (b'TUV', b'Tuvalu'), (b'UGA', b'Uganda'), (b'UKR', b'Ukraine'), (b'ARE', b'United Arab Emirates'), (b'GBR', b'United Kingdom'), (b'TZA', b'United Republic of Tanzania'), (b'USA', b'United States of America'), (b'VIR', b'United States Virgin Islands'), (b'URY', b'Uruguay'), (b'UZB', b'Uzbekistan'), (b'VUT', b'Vanuatu'), (b'VEN', b'Venezuela (Bolivarian Republic of)'), (b'VNM', b'Viet Nam'), (b'WLF', b'Wallis and Futuna Islands'), (b'ESH', b'Western Sahara'), (b'YEM', b'Yemen'), (b'ZMB', b'Zambia'), (b'ZWE', b'Zimbabwe')]),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='delivery',
            field=models.CharField(help_text='physical and email address at which the organization or individual may be contacted', max_length=255, null=True, verbose_name='Delivery Point', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='email address', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='fax',
            field=models.CharField(help_text='telephone number of a facsimile machine for the responsible organization or individual', max_length=255, null=True, verbose_name='Facsimile', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='first_name',
            field=models.CharField(max_length=30, verbose_name='first name', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='keywords',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='commonly used word(s) or formalised word(s) or phrase(s) used to describe the subject (space or comma-separated', verbose_name='keywords'),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='last_name',
            field=models.CharField(max_length=30, verbose_name='last name', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='organization',
            field=models.CharField(help_text='name of the responsible organization', max_length=255, null=True, verbose_name='Organization Name', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='position',
            field=models.CharField(help_text='role or position of the responsible person', max_length=255, null=True, verbose_name='Position Name', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='voice',
            field=models.CharField(help_text='telephone number by which individuals can speak to the responsible organization or individual', max_length=255, null=True, verbose_name='Voice', blank=True),
        ),
        migrations.AddField(
            model_name='contactrole',
            name='zipcode',
            field=models.CharField(help_text='ZIP or other postal code', max_length=255, null=True, verbose_name='Postal Code', blank=True),
        ),
        migrations.AlterField(
            model_name='contactrole',
            name='contact',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='contactrole',
            unique_together=set([('resource', 'role')]),
        ),
    ]
