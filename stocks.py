import csv
import random
import statistics
import numpy
import fitter
from scipy.stats import johnsonsu

dates = []
data = []
with open('spy20yr9july2020.csv') as csvfile:
	reader = csv.reader(csvfile, delimiter=',')
	for row in reader:
		data.append(row)
		dates.append(row[2])

days_back = [30, 60, 90, 180, 270, 365]

print('Days Back' + ',' + 'Days Forward' + ',' + 'Percent Success')

for back in days_back:
	for forward in range(5, 30, 5):
		total_count = 0
		success_count = 0
		for date in range(1170, 5160):
			#base_index = dates.index(date)
			base_index = date
			if base_index - back >= 1169 and base_index + forward < len(dates):
				past_changes = []
				for i in range(base_index, base_index-back, -1):
					p_open = float(data[i][5])
					p_close = float(data[i][4])
					daily_percent_return = (p_close - p_open)/(p_open)
					#daily_point_change = p_close - p_open
					past_changes.append(daily_percent_return)
					#past_changes.append(daily_point_change)
				#pc_mean = statistics.mean(past_changes)
				#pc_sd = statistics.pstdev(past_changes)
				f = Fitter(past_changes)
				f.distributions = ['johnsonsu'] + ['nct'] + ['norminvgauss'] + ['t']
				f.fit()
				f.summary()
				params = f.fitted_param['johnsonsu']
				estimates = []
				for j in range(1, 10000):
					#sample = random.choices(past_changes, k=forward)
					#sample = numpy.random.normal(loc=pc_mean, scale=pc_sd, size=forward)
					sample = johnsonsu.rvs(params[0], params[1], loc=params[2], scale=params[3], size=forward)
					estimate = float(data[base_index][5])
					for s in sample:
						estimate = estimate * (1 + s)
					#estimate = estimate + s
					estimates.append(estimate)

				sd = statistics.pstdev(estimates)
				mean = statistics.mean(estimates)
				lower = float(mean - sd)
				upper = float(mean + sd)
				actual_closing_price = float(data[base_index + forward][4])
				if lower <= actual_closing_price <= upper:
					success_count += 1
					total_count += 1
					#print(str(dates[date]) + ',' + str(back) + ',' + str(forward) + ',' + str(mean) + ',' + str(sd) + ',' + str(lower) + ',' + str(upper) + ',' + str(actual_closing_price) + ',' + 'S')
				else:
					total_count += 1
					#print(str(dates[date]) + ',' + str(back) + ',' + str(forward) + ',' + str(mean) + ',' + str(sd) + ',' + str(lower) + ',' + str(upper) + ',' + str(actual_closing_price) + ',' + 'F')
		percent_success = float(success_count / total_count)
		print(str(back) + ',' + str(forward) + ',' + str(percent_success))
#print('Mean: ' + str(mean))
#print('SD: ' + str(sd))
#print('Range: (' + str(lower) + ', ' + str(upper) + ')')
#print('Actual Closing Price: ' + str(actual_closing_price))