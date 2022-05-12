from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
import time
from PIL import Image
import random
import cv2
import numpy as np

driver = None
sliding_pic_path = './sliding.png' # 缺损块图路径
defect_pic_path = './defect.png' # 缺损图路径
full_pic_path = './full.png' # 完整图路径
result_pic_path = './result.png' # 处理结果图路径


def reset_html():
	js_show_defect_pic = 'document.getElementsByClassName("geetest_canvas_bg geetest_absolute")[0].style.display="block"' # 显示缺损图
	js_show_sliding_pic = 'document.getElementsByClassName("geetest_canvas_slice geetest_absolute")[0].style.display="block"' # 显示缺损块
	js_hide_full_pic = 'document.getElementsByClassName("geetest_canvas_fullbg geetest_fade geetest_absolute")[0].style.display="none"' # 隐藏完整图
	driver.execute_script(js_show_defect_pic + ';' + js_show_sliding_pic + ';' + js_hide_full_pic)


def get_defect_pic():
	'''截取缺损图'''
	js_hide_slice = 'document.getElementsByClassName("geetest_canvas_slice geetest_absolute")[0].style.display="none"' # 隐藏滑块
	driver.execute_script(js_hide_slice)

	driver.find_element(By.XPATH, '/html/body/div[@style="display: block; opacity: 1;"][1]/div[2]/div[6]/div/div[1]/div[1]/div/a/div[1]/div/canvas[1]').screenshot(defect_pic_path)
	reset_html()


def get_sliding_pic():
	'''截取缺损块'''
	js_hide_defect_pic = 'document.getElementsByClassName("geetest_canvas_bg geetest_absolute")[0].style.display="none"' # 隐藏缺损图
	driver.execute_script(js_hide_defect_pic)
	
	driver.find_element(By.XPATH, '/html/body/div[@style="display: block; opacity: 1;"][1]/div[2]/div[6]/div/div[1]/div[1]/div/a/div[1]/div/canvas[2]').screenshot(sliding_pic_path)
	reset_html()


def get_full_pic():
	'''截取全图'''
	js_hide_defect_pic = 'document.getElementsByClassName("geetest_canvas_bg geetest_absolute")[0].style.display="none"' # 隐藏缺损图
	js_hide_slice = 'document.getElementsByClassName("geetest_canvas_slice geetest_absolute")[0].style.display="none"' # 隐藏滑块
	js_show_full_pic = 'document.getElementsByClassName("geetest_canvas_fullbg geetest_fade geetest_absolute")[0].style.display="block"' # 显示完整图
	driver.execute_script('{};{};{}'.format(js_hide_defect_pic, js_hide_slice, js_show_full_pic))

	driver.find_element(By.XPATH, '/html/body/div[@style="display: block; opacity: 1;"][1]/div[2]/div[6]/div/div[1]/div[1]/div/a/div[1]/canvas').screenshot(full_pic_path)
	reset_html()


def get_offset_defect(defect_pic_path, full_pic_path):
	'''获取缺口横坐标'''
	defect_pic = Image.open(defect_pic_path)
	full_pic = Image.open(full_pic_path)
	w, h = defect_pic.size
	max_value_offset = 0
	x_pos = 0
	for x in range(w):
		for y in range(h):
			defect_rgb = defect_pic.getpixel((x, y))
			full_rgb = full_pic.getpixel((x, y))
			# 比较色差
			r = defect_rgb[0] - full_rgb[0]
			g = defect_rgb[1] - full_rgb[1]
			b = defect_rgb[2] - full_rgb[2]
			values = abs(r) + abs(g) + abs(b)
			if values > max_value_offset:
				max_value_offset = values
				x_pos = x
			if values > 60: # 色差较大
				return x
			else:
				print('未找到色差大的区域,最大色差{}'.format(max_value_offset))
	return x_pos


def get_offset_sliding(sliding_pic_path):
	'''获取滑块坐标'''
	sliding_pic = Image.open(sliding_pic_path)
	w, h = sliding_pic.size
	# 滑块为彩色，其余地方为白色
	for x in range(w):
		for y in range(h):
			rgb = sliding_pic.getpixel((x, y))
			value = rgb[0] + rgb[1] + rgb[2]
			if value < 550:
				return x


def move_slice(distance):
	'''直线拉动滑块'''
	element = driver.find_element(By.CLASS_NAME, 'geetest_slider_button')
	action = ActionChains(driver)
	action.click_and_hold(element)
	action.move_by_offset(xoffset=distance, yoffset=0)
	action.pause(0.4)
	action.release(element)
	action.perform()


def get_track_by_step(distance):
	'''获取轨迹，随机步长'''
	tracks = [] # #轨迹列表，每个元素代表0.2s的位移
	current = 0 # 当前的位移总量
	mid = distance * 5 / 8 # 中段距离，达到mid开始减速
	# 大步长的上下限长度，通过小数可以控制步数
	# 如下设置参数为0.3 0.5，可以保证前半段路径长度为2-4步完成
	big_step_bottom = round(mid * 0.3)
	big_step_top = round(mid * 0.5)
	while current <= distance + 5: # 设定偏移量，先滑过一点，最后再反着滑动回来
		if current < mid: # 前半段大步长
			step = random.randint(big_step_bottom, big_step_top)
		else: # 后半段小步长
			step = random.randint(2, (distance - current + 5) if (distance - current + 5 > 2) else 3)
		current += step
		tracks.append(step)
	while (current - distance) > 1:
		step = -random.randint(1, current - distance)
		tracks.append(step)
		current += step
	print('理论总长：{}， 实际路长：{}，路径为:{}'.format(str(distance), str(current), str(tracks)))
	return tracks


def move_random(distance):
	'''随机步长拉动滑块'''
	element = driver.find_element(By.CLASS_NAME, 'geetest_slider_button')
	action = ActionChains(driver, duration=250)
	action.click_and_hold(element)
	action.pause(0.4)
	tracks = get_track_by_step(distance)
	for track in tracks:
		action.move_by_offset(xoffset=track, yoffset=0)
	action.pause(0.8)
	action.release(element)
	action.perform()



def get_track(distance):
	'''
	获得移动轨迹，模仿人的滑动行为，先匀加速后匀减速匀变速运动基本公式:
	①v=v0+at
	②s=v0t+0.5at^2
	:param distance: 需要移动的距离
	:return: 每0.2s移动的距离
	'''
	v0 = 0 # 初速度
	t = 0.2 # 单位时间 0.2s
	tracks = [] # #轨迹列表，每个元素代表0.2s的位移
	current = 0 # 当前的位移总量
	mid = distance * 5 / 8 # 中段距离，达到mid开始减速
	while current <= distance + 5: # 设定偏移量，先滑过一点，最后再反着滑动回来
		t = random.randint(1,4) / 10 # 增加运动随机性
		if current < mid: # 加速度越小，单位时间的位移越小，模拟的轨迹就越多越详细
			a = random.randint(2,7) # 加速运动
		else:
			a = -random.randint(2,6) # 减速运动
		s = v0 * t + 0.5 * a * (t**2) # 单位时间内的位移量
		current += round(s + 1) # 当前位移总量
		tracks.append(round(s + 1)) # 添加到轨迹列表
		v0 = v0 + a # 更新初速度
	#反着滑动到大概准确位置        
	# for i in range(4):
	# 	tracks.append(-random.randint(1,3))
	while (current - distance) > 1:
		step = -random.randint(1,3)
		tracks.append(step)
		current += step
	print('理论总长：{}，实际路长：{}，路径为:{}'.format(str(distance), str(current), str(tracks)))
	return tracks


def move_like_human(distance):
	'''模拟人行为拉动滑块'''
	element = driver.find_element(By.CLASS_NAME, 'geetest_slider_button')
	action = ActionChains(driver, duration=50)
	action.click_and_hold(element)
	action.pause(0.4)
	tracks = get_track(distance)
	for track in tracks:
		action.move_by_offset(xoffset=track, yoffset=0)
	action.pause(0.8)
	action.release(element)
	action.perform()


def get_color_different(defect_pic_path, full_pic_path):
	'''数据量化两幅图RGB颜色差值

	input:
		defect_pic_path: 缺损图路径
		full_pic_path: 完整图路径

	return:
		x: 缺损图最左坐标
	'''
	defect_img = cv2.imread(defect_pic_path)
	full_img = cv2.imread(full_pic_path)
	blank_img = np.zeros_like(defect_img)

	defect_gray_img = cv2.cvtColor(defect_img, cv2.COLOR_BGR2GRAY)
	full_gray_img = cv2.cvtColor(full_img, cv2.COLOR_BGR2GRAY)

	diff_rgb_img = defect_img - full_img
	diff_gray_img = defect_gray_img - full_gray_img
	diff_gray_img_processing = diff_gray_img.copy()
	diff_gray_img_processing[diff_gray_img > 200] = 0
	diff_gray_img_processing[diff_gray_img < 10] = 0
	x = min(np.where(diff_gray_img_processing.sum(axis=0) > 500)[0])

	stackImage = stackImages(1, ([defect_img, defect_gray_img, blank_img], [full_img, full_gray_img, blank_img], [diff_rgb_img, diff_gray_img, diff_gray_img_processing]))

	cv2.imshow('stackImage', stackImage)
	cv2.imwrite(result_pic_path, stackImage)
	cv2.waitKey(10)
	return x


def stackImages(scale, imgArray):
    rows = len(imgArray)
    cols = len(imgArray[0])
    # & 输出一个 rows * cols 的矩阵（imgArray）
    # & 判断imgArray[0] 是不是一个list
    rowsAvailable = isinstance(imgArray[0], list)
    # & imgArray[][] 是什么意思呢？
    # & imgArray[0][0]就是指[0,0]的那个图片（我们把图片集分为二维矩阵，第一行、第一列的那个就是第一个图片）
    # & 而shape[1]就是width，shape[0]是height，shape[2]是
    width = imgArray[0][0].shape[1]
    height = imgArray[0][0].shape[0]

    if rowsAvailable:
        for x in range (0, rows):
            for y in range(0, cols):
                # & 判断图像与后面那个图像的形状是否一致，若一致则进行等比例放缩；否则，先resize为一致，后进行放缩
                if imgArray[x][y].shape[:2] == imgArray[0][0].shape [:2]:
                    imgArray[x][y] = cv2.resize(imgArray[x][y], (0, 0), None, scale, scale)
                else:
                    imgArray[x][y] = cv2.resize(imgArray[x][y], (imgArray[0][0].shape[1], imgArray[0][0].shape[0]), None, scale, scale)
                # & 如果是灰度图，则变成RGB图像（为了弄成一样的图像）
                if len(imgArray[x][y].shape) == 2: imgArray[x][y]= cv2.cvtColor( imgArray[x][y], cv2.COLOR_GRAY2BGR)
        # & 设置零矩阵
        imageBlank = np.zeros((height, width, 3), np.uint8)
        hor = [imageBlank]*rows
        hor_con = [imageBlank]*rows
        for x in range(0, rows):
            hor[x] = np.hstack(imgArray[x])
        ver = np.vstack(hor)
    # & 如果不是一组照片，则仅仅进行放缩 or 灰度转化为RGB
    else:
        for x in range(0, rows):
            if imgArray[x].shape[:2] == imgArray[0].shape[:2]:
                imgArray[x] = cv2.resize(imgArray[x], (0, 0), None, scale, scale)
            else:
                imgArray[x] = cv2.resize(imgArray[x], (imgArray[0].shape[1], imgArray[0].shape[0]), None,scale, scale)
            if len(imgArray[x].shape) == 2: imgArray[x] = cv2.cvtColor(imgArray[x], cv2.COLOR_GRAY2BGR)
        hor= np.hstack(imgArray)
        ver = hor
    return ver


if __name__ == '__main__':
	driver = webdriver.Chrome()
	driver.get('https://captcha1.scrape.center/')
	driver.implicitly_wait(3)

	driver.find_element(By.XPATH, '//*[@id="app"]/div[2]/div/div/div/div/div/form/div[3]/div/button').click()
	isLoadCaptcha = False
	while not isLoadCaptcha:
		try:
			print('匹配中...')
			WebDriverWait(driver, 8, 2).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[@style="display: block; opacity: 1;"][1]/div[2]/div[6]/div/div[1]/div[1]/div/a/div[1]/canvas'))) # 有时页面会加载两个验证div，需要使用属性过滤一下
			isLoadCaptcha = True
		except TimeoutException:
			print('未命中，准备下一次....')
			try:
				driver.find_element(By.XPATH, '//*[@id="app"]/div[2]/div/div/div/div/div/form/div[3]/div/button').click()
			except ElementClickInterceptedException: # 
				pass
		except Exception:
			pass
	time.sleep(3) # 等待图片加载

	get_defect_pic()
	get_sliding_pic()
	get_full_pic()

	# defect_offset = get_offset_defect(defect_pic_path, full_pic_path) # 缺口坐标 - 使用彩色RGB差值获取
	defect_offset = get_color_different(defect_pic_path, full_pic_path) # 缺口坐标 - 使用灰度图差值获取
	sliding_offset = get_offset_sliding(sliding_pic_path) # 滑块坐标
	sliding_length = abs(defect_offset - sliding_offset) # 需要滑动距离

	# move_slice(sliding_length) # 直接拖动
	move_like_human(sliding_length) # 模拟人类行为拖动
	# move_random(sliding_length) # 随机路径长度拖动
	time.sleep(2)

	try:
		EC.presence_of_element_located((By.CLASS_NAME, 'geetest_success_animate')).__call__(driver) # 查找成功显示页
		print('验证成功')
	except Exception:
		print('验证失败')
	time.sleep(5)

	driver.close()
	driver.quit()
	
	# get_color_different(defect_pic_path, full_pic_path) # 测试图像