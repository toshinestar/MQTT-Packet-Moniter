import pyodbc
import xlrd
server = input("Server name--For example: (localdb)\MSSQLLocalDB :")
database = input("Database name :")
cnxn_str = ("Driver={ODBC Driver 17 for SQL Server};"
            "Server="+server+";"
            "Database="+database+";"
            "Trusted_Connection=yes;")
excel_file = input("Excel file :")
data = xlrd.open_workbook(excel_file)
sheet_name = input("Excel Sheet name :")
sheet = data.sheet_by_name(sheet_name)
cnxn = pyodbc.connect(cnxn_str)
cursor = cnxn.cursor()

query = """
INSERT INTO [dbo].[PCS_Net_Flex_Thous] (
    RdwyId,
    SurveyYear,
    RdwyDirec,
    BMP,
    EMP,
    RutAvg,
    IRI1,
    IRI2,
    IRIA,
    RN1,
    RN2,
    RNC,
    SecSpeed,
    Lat,
    Long,
    FlexId
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""


for r in range(1, sheet.nrows):
    file_name = sheet.cell(r, 0).value
    survey_year = sheet.cell(r, 1).value
    rdwy_direc = sheet.cell(r, 2).value
    bmp = sheet.cell(r, 3).value
    emp = sheet.cell(r, 4).value
    profiler_rutavg = sheet.cell(r, 5).value
    iri_left = sheet.cell(r, 6).value
    iri_right = sheet.cell(r, 7).value
    iri_avg = sheet.cell(r, 8).value
    rn_left = sheet.cell(r, 9).value
    rn_right = sheet.cell(r, 10).value
    rn_combined = sheet.cell(r, 11).value
    sec_speed = sheet.cell(r, 12).value
    gps_lat = sheet.cell(r, 13).value
    gps_lon = sheet.cell(r, 14).value
    
    # Assing values from each row
    substr = file_name[0:1]
    i = 0
    new_file_name = ""
    while(substr.isnumeric()):
        new_file_name = new_file_name + substr
        i = i + 1
        substr = file_name[i:i+1]
        
    new_file_name = new_file_name + "000"

    fid_query = "SELECT * FROM PCS_Net_Flex WHERE RdwyId = " + new_file_name +" AND BMP > " + str(bmp) + " AND EMP < " + str(emp) + " AND RdwyDirec = '" + rdwy_direc + "' AND SurveyYear = " + str(survey_year)
    cursor.execute(fid_query)
    result = cursor.fetchone()

    fid = 0
    if result:
        fid = result[15]

    values = (new_file_name, survey_year, rdwy_direc, bmp, emp,
              profiler_rutavg, iri_left, iri_right, iri_avg, rn_left,
              rn_right, rn_combined, sec_speed, gps_lat, gps_lon, fid)
    
    cursor.execute(query, values)
    print("Insert row {} Success".format(r))
cnxn.commit()
