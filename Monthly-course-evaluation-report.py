thisCourseOnly = ""  #PRE HOSP PEM, , Leave empty for ALL Courses. 
startDate      = ""  # YYYY-MM-DD, Leave empty for last month
endDate        = ""  # YYYY-MM-DD, Leave empty for last month
directoryName  = ""  # Leave Empty for last month YYYY-MM in Analysis directory
####################################################################
#  This is the end of the section where you can change variables   #
####################################################################
import pandas as pd
import math
import os
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from scipy import stats
import cx_Oracle
import datetime
from dateutil.relativedelta import relativedelta
#%matplotlib inline  #Only for Jupyter Notebooks
#Make the print() statement print real wiiiiiiiddddeee
pd.set_option('display.width', 500)

#figure out what is last months dates
today = datetime.date.today()
firstOfThisMonth = today.replace(day=1)
firstOfLastMonth = firstOfThisMonth - relativedelta(months=1)
lastOfLastMonth  = firstOfThisMonth - datetime.timedelta(days=1)
#set these values automatically to last month if they are not set already.
if directoryName == "":
    directoryName = firstOfLastMonth.strftime("%Y-%m") 
if startDate == "":
    startDate = firstOfLastMonth.strftime("%Y-%m-%d") 
if endDate == "":
    endDate = lastOfLastMonth.strftime("%Y-%m-%d")  

# These are the questions that we'll be graphing.
# The dictionary key does *not* need to be one character.
questionDict = {'E' : 'Effectiveness of the in-person education you received',
                'L' : 'Likeliness of recommending this course to a colleague', 
                'F' : 'The facilitator(s) made the educational experience relevant to my training level'
               }

#Make the output directory for the PDF files
outFilePath = "Analysis/Course-Evaluations/" +directoryName+"/"
Path(outFilePath).mkdir(parents=True, exist_ok=True)
print ("Creating PDF files in : " +outFilePath)

#Get last month's data from the Oracle Database
dsn_tns    = cx_Oracle.makedsn("y27prd01.isd.upmc.edu",1521, "SIMP2")
# connection = cx_Oracle.connect('simmedical_prod', 'PROD7892', "y27prd01.isd.upmc.edu:1521/SIMP2")
connection = cx_Oracle.connect('simmedical_prod', 'PROD7892', dsn_tns)
selectStr = """select c.ABBRV COURSE, c.COURSE_ID, to_char(l.CLASS_DATE, 'YYYY-MM-DD') CLASS_DATE,
       l.CLASS_ID, a.EVAL_ANSWER_ID SCORE, to_char(m.EVALUATE_DATE, 'YYYY-MM-DD HH24:MI:SS') EVALUATE_DATE,
       case when instr(q.QUESTION_TEXT, 'Effectiveness') > 1 then 'E'
            when instr(q.QUESTION_TEXT, 'Likeliness')    > 1 then 'L'
       else 'F' END "TYPE" --Facilitator
  from EVALUATION_ANSWERS a, EVALUATION_MAIN m, CLASSES l, courses c, ID0_EVAL_QUESTIONS q
 where a.EVALUATION_ID = m.EVALUATION_ID
   and a.EVAL_QUESTION_ID = q.EVAL_QUESTION_ID
   and m.CLASS_ID = l.CLASS_ID
   and l.COURSE_ID = c.COURSE_ID
   -- This will pull the data from last month (if you run it before the 28th of the month).
   and trunc(m.EVALUATE_DATE) between to_date('2019-07-01', 'YYYY-MM-DD')
                                  and trunc(sysdate,    'mm')-1
--   and trunc(m.EVALUATE_DATE) < to_date('2020-05-01', 'YYYY-MM-DD')
   -- Effectiveness of the in-person education you received
   and (a.EVAL_QUESTION_ID in (36277, 36336, 36348, 36613, 36858, 36927, 37139, 37180, 37217, 37240, 37284, 37406, 37418, 37724, 37966, 38069, 38108, 38220)
       -- Likeliness of recommending this course to a colleague
        or a.EVAL_QUESTION_ID in (36855, 36924, 37136, 37176, 37192, 37194, 37214, 37237, 37281, 37299, 37403, 37415, 37721, 37831, 37951, 37963, 38066, 38105, 38219)
      -- The facilitator(s) made the educational experience relevant to my training level
        or a.EVAL_QUESTION_ID in (36280, 36339, 36351, 36616, 36861, 36930, 37142, 37183, 37220, 37244, 37287, 37409, 37421, 37727, 37969, 38072, 38111, 38223)
        )
order by EVALUATE_DATE"""
df = pd.read_sql_query(selectStr, con=connection, parse_dates={'CLASS_DATE','EVALUATE_DATE'})

print("Reading {} records. ".format(df.shape[0]))
#get rid of any non responses.
df.replace(-999.0, np.NaN, inplace=True)
df.dropna(inplace=True)
print("{} records after removing null values. ".format(df.shape[0]))

#Filter by the start and end dates
df2 = df[(df.CLASS_DATE>=pd.to_datetime(startDate))]
df3 = df2[(df2.CLASS_DATE<=pd.to_datetime(endDate))]

print("{0:} records beween {1:} and {2:}.".format(df3.shape[0], startDate, endDate))

#These are the headers of the columns for the ce dataframe that we will generate the plots from
theColumnList = ["the1s","the2s","the3s","the4s","the5s"]

# Pivot, compressing the scores to counts of each score (1-5)
pivoted = df3.pivot_table(index=["COURSE", "TYPE"],
                          columns="SCORE",
                          aggfunc={'SCORE':np.count_nonzero}
                        )
#cpd will be the compressed, pivoted data
cpd = pd.DataFrame(pivoted.to_records())
cpd.fillna(0, inplace=True) #clean out the NaNs

#clean out the header cruft from when we created the Pivot Table.
cpd.columns = [hdr.replace("('SCORE', ", "").replace(")", "") for hdr in cpd.columns]

#Need to rename the columns to alphnumeric names to reference them below
cpd.rename(columns={"1.0":"the1s", "2.0":"the2s", "3.0":"the3s", "4.0":"the4s", "5.0":"the5s"}, inplace=True)

#There may be no data for some of the columns (no 1s for example),
#so we may need to create columns with zeros avoid errors below.
colCnt = 2
for col in theColumnList : 
    if col not in cpd.columns :
        cpd.insert(colCnt, col, 0)
    colCnt += 1

#Create a new TOTAL column which is a sum of the columns 1-5
cpd.eval('TOTAL=@cpd.the1s+@cpd.the2s+@cpd.the3s+@cpd.the4s+@cpd.the5s', inplace=True)    

print (cpd)
   
#these will be the columns for the new totalsDF Dataframe
totalsColumns = theColumnList+ ["TOTAL"]
totalsDF = pd.DataFrame(columns=totalsColumns, index=questionDict.keys())
#Calculate the totals of each column and put it in a dataframe.
#We will use this to get the percentage for each course.
for key in questionDict : 
    totalAll = 0
    for hdr in theColumnList :
        #Calculate the totals
        totalsDF.loc[key,hdr] = cpd[(cpd.TYPE==key)][hdr].sum()
        totalAll +=  totalsDF.loc[key,hdr]
    totalsDF.loc[key, "TOTAL"] = totalAll

print("The totalsDF is : ")
print(totalsDF)
    
#Now create a Dataframe with the percentages of the totals
totalPercColumns = theColumnList
totalPercDF = pd.DataFrame(columns=totalPercColumns, index=questionDict.keys())
for key in questionDict : 
    for hdr in theColumnList :
        totalPercDF.loc[key,hdr]=(totalsDF.loc[key,hdr]/totalsDF.loc[key,"TOTAL"])*100

print("The totalsPercDF is : ")
print (totalPercDF)

#Get the list of courses.
courseList = cpd.COURSE.unique()

#this is the X Axis for the graphs
x = np.array([1, 2, 3, 4, 5])

#Set some counts.
plotCnt   =  0
courseCnt = 0
for course in courseList :
    if (course==thisCourseOnly or thisCourseOnly == "") :
        # Set up 3 stacked plots on this figure
        plt.style.use('seaborn-deep') #Nice dark style - seaborn-deep
        fig, axs = plt.subplots(3, sharex=True)
        fig.suptitle(course+"\n"+startDate+ " - " +endDate+ "\n")
        fig.set_size_inches(7.5,10)
#         fig.xlabel('Likert 1-5')
        axCnt = 0
        barWidth = .40
        for key in questionDict :
            # Reset the percentage arrays
            #filter to get a dataframe with just this course and this question
            theDF = cpd[(cpd.COURSE==course) & (cpd.TYPE==key)]
#             print("The DF is:")
#             print(theDF)
            if (theDF.size) : #Make sure we have data for this question
                thisCoursePerc = []
                totalCoursePerc = []
                for col in theColumnList :
                    #get the percentages from the filtered dataframe
                    thisCoursePerc.append(float((theDF[col]/theDF["TOTAL"])*100))
                    totalCoursePerc.append(totalPercDF.loc[key,col])
                df = pd.DataFrame({'All Courses' : totalCoursePerc, 'This Course' : thisCoursePerc},
                                index=x)
                #start plotting
                axs[axCnt].bar(x, df['This Course'], width=.4)
                axs[axCnt].bar(x+barWidth, df['All Courses'], width=.4)
                axs[axCnt].legend(['This Course n = {}'.format(int(theDF["TOTAL"])),\
                                   'All Courses n = {}'.format(int(totalsDF.loc[key,"TOTAL"])),],
                                  loc='upper left')
                axs[axCnt].set_xticks(x + barWidth/2)
                axs[axCnt].set_xticklabels(x)
                axs[axCnt].set_ylim(0,100)
                axs[axCnt].set_ylabel("Percent")
                axs[axCnt].set_title(questionDict[key])
                axs[axCnt].grid(b=True, axis='y', color='gray')
                axCnt += 1
        # Label the bottom X Axis Only
        axs[axCnt-1].set_xlabel("Likert 1-5")
#         print(course+ " totals are: ")
#         print(totalPercDF.head())
        plotCnt += 1
        courseCnt += 1
        outFileStr = outFilePath+course+ '-' +startDate+ '-' +endDate+ '.pdf'
#         plt.show()  #waaaaaay to many plots on the screen.
        fig.savefig(outFileStr)
        print('.', end='') #mark our progress through the data.
        plt.close()

if plotCnt==1 :
    graphStr = " graph"
else :
    graphStr =  " graphs"
if courseCnt==1 :
    courseStr = " course."
else :
    courseStr = " courses."
print ("\n" +graphStr+ " created for " +str(courseCnt)+ courseStr)