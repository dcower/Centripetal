"""
CENTRIPETAL!

Sorry for the messy code! I only found out about the contest ~2 days
before it was over, so I didn't have much time to write nice code. :(

Copyright 2012 Dillon Cower, d <last name> @ gmail . com
"""
import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty
from kivy.vector import Vector
from kivy.factory import Factory
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Point, GraphicException, Line, Quad, Ellipse
from kivy.graphics.opengl import glLineWidth
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.core.window import Window
from cmath import polar, rect
from kivy.core.audio import SoundLoader
from math import cos,sin,pi,sqrt,atan,atan2
import random

cx = 0
cy = 0

# The collision functions are somewhat based around code by papalazaru and Dave Eberly:
# http://www.gamedev.net/topic/546941-circle-to-polygon-collision-detection-solved/
def circleToPolygon(circle, quad):
	cpos = Vector(circle.pos[0], circle.pos[1])

	x = cpos[0]
	y = cpos[1]
	r = circle.r
	r2 = circle.r2
	w = quad

	if (x+r > w.lowerx) and (x-r < w.upperx) and (y+r > w.lowery) and (y-r < w.uppery):
		quad = quad.pts
		#print random.randint(0,1000000)
		
		# for each edge
		best_closest = None
		normal = None
		best_d = None
		for i in range(4):
			edge_pt1 = Vector(float(quad[i*2]), float(quad[(i*2+1)]))
			edge_pt2 = Vector(float(quad[((i+1)*2)%8]), float(quad[((i+1)*2+1)%8]))
			pt = closestPointOnEdge(cpos, edge_pt1, edge_pt2)

			d = pt.distance2(cpos)

			if d < r2 and (best_d is None or d < best_d):
				closest = pt
				normal = edge_pt2 - edge_pt1
				normal = Vector(-normal.y, normal.x).normalize()
				best_d = d
				#return (True, closest, normal)
		if best_d is not None:
			return (True, closest, normal)
		
		# if we still haven't gotten anything, try this test..
		if polygonContainsPoint(cpos, quad):
			#print "GRRRRRRR"
			return (True, cpos, cpos.normalize())

	return (False, None, None)

def polygonContainsPoint(p, quad):
	flags = 0

	i = 0
	j = 4-1

	c = False
	testx = p[0]
	testy = p[1]

	while i < 4:
		edge_pt1 = (float(quad[i*2]), float(quad[(i*2+1)]))
		edge_pt2 = (float(quad[((i+1)*2)%8]), float(quad[((i+1)*2+1)%8]))

		if ((edge_pt1[1] > testy) != (edge_pt2[1] > testy)) and (testx < (edge_pt2[0] - edge_pt1[0]) * (testy-edge_pt1[1]) / (edge_pt2[1]-edge_pt1[1]) + edge_pt1[0]):
			c = ~c

		j = i
		i+=1
	
	return c

def circleToCircle(a, b):
	v = Vector(a.pos) - Vector(b.pos)

	if v.length() < a.r+b.r:
		return (True, None, v.normalize())
	
	return (False, None, None)

# Vector p point
# Vector a edge_pt1
# Vector b edge_pt2
def closestPointOnEdge(p, a, b):
	e = b - a
	f = p - a
	e2 = e.length2()

	if e2 != 0:
		t = (f.dot(e)) / e2
	else:
		t = 0.0

	if t < 0.0:
		t = 0.0
	elif t > 1.0:
		t = 1.0

	closest = a + (e * t)

	return closest


class Ball(Widget):
	r = 30 / 2
	r2 = r**2

	trail_pts = []
	g_trail = "trail"

	def setup(self):
		self.pos = (cx, cy+cy/2)
		self.velocity = Vector(0,5)

	def move(self, dt):
		self.canvas.remove_group(self.g_trail)
		with self.canvas:
			Color(1, 1, 1, 0.5, mode='rgba', group=self.g_trail)
			Line(points=sum(self.trail_pts, []), group=self.g_trail)

		to_center = (Vector(cx, cy) - Vector(self.pos))

		l = self.velocity.length()
		cen_d = to_center.length()
		self.velocity = self.velocity * 0.99 + to_center.normalize() * sqrt(cen_d) * 0.04

		if l > 25:
			self.velocity = self.velocity.normalize() * 20
		self.pos = Vector(self.pos) + self.velocity * dt * 30

		if len(self.trail_pts) == 0:
			self.trail_pts = [self.pos]
		else:
			self.trail_pts.insert(0, self.pos)

		while len(self.trail_pts) > 30:
			self.trail_pts.pop()


class Block(Widget):
	def collide_widget(self, wid):
		return circleToPolygon (wid, self)


class CentripetalGame(Widget):
	g_level = "level"
	paddle = ObjectProperty(None)
	ball = ObjectProperty(None)
	killspace = ObjectProperty(None)
	score = NumericProperty(0)
	best_score = NumericProperty(0)
	sounds = {}
	blocks = []

	def start(self):
		# are these necessary? no time to find out!!!!!!
		self.width = Window.width
		self.height = Window.height
		self.size = Window.size

		for i in ["hit", "hit_2", "die"]:
			if i not in self.sounds:
				self.sounds[i] = SoundLoader.load(i + ".ogg")
				self.sounds[i].volume = 0.8
		
		self.n_rings = 3
		self.num_segments = 10
		self.generate_level()

		self.paddle.move(pi/2)
		self.ball.setup()
		self.killspace.pos = (cx, cy)

		self.score = 0
		self.level_num = 0

		with self.canvas:
			glLineWidth(3)

	def generate_level(self):
		for w in self.blocks:
			self.remove_widget(w)

		self.canvas.remove_group(CentripetalGame.g_level)
		self.blocks = []

		color = 0
		width = min(Window.width, Window.height)

		#r_start = 300
		n_rings = self.n_rings
		#num_segments = self.num_segments
		num_segments = n_rings + 7
		ring_spacing = width / 60.0 / n_rings * 7 	# maybe this shouldn't depend on the window width/height?

		r_start = width/2 - ring_spacing * n_rings

		for ring in range(n_rings):
			r_1 = ring * ring_spacing + r_start
			r_2 = (ring+1) * ring_spacing + r_start
			#num_segments = ring*4
			step = (2*pi)/num_segments
			for i in range(num_segments):
				angle = step * i
				#color += random.uniform(0,0.5)
				color += random.uniform(0,1.0 / (num_segments * n_rings) * 2)
				w = Block()
				self.add_widget (w)
				pts=[
								cx + cos(angle)*r_1, cy + sin(angle)*r_1,
								cx + cos(angle)*r_2, cy + sin(angle)*r_2,
								cx + cos(angle + step)*r_2, cy + sin(angle + step)*r_2,
								cx + cos(angle + step)*r_1, cy + sin(angle + step)*r_1
								]
				w.pts = pts
				w.lowerx = pts[0]
				w.lowery = pts[1]
				w.upperx = pts[0]
				w.uppery = pts[1]

				for i in range(0, 8, 2):
					if pts[i] < w.lowerx: w.lowerx = pts[i]
					if pts[i] > w.upperx: w.upperx = pts[i]
					if pts[i+1] < w.lowery: w.lowery = pts[i+1]
					if pts[i+1] > w.uppery: w.uppery = pts[i+1]
				
				with w.canvas:
					Color(color, random.uniform(0.4,1), random.uniform(0.8,1), mode='hsv', group=CentripetalGame.g_level)
					Quad(points=pts, group=CentripetalGame.g_level)
				self.blocks.append(w)
		
	
	def on_touch_down(self,touch):
		self.on_touch_move(touch)

	def on_touch_move(self, touch):
		angle = atan2 (touch.y - cy, touch.x - cx)

		self.paddle.move (angle)

		#self.ball.pos = (touch.x, touch.y)

	def on_touch_up(self,touch):
		self.on_touch_move(touch)
	
	def update(self, dt):
		self.ball.move(dt)
		col = self.paddle.collide_widget(self.ball)

		if col[0]:
			#print dt,"bam"
			self.sounds["hit_2"].play()
			d = self.ball.r + self.paddle.r - (Vector(self.ball.pos) - Vector(self.paddle.pos)).length()
			#print d
			self.ball.pos = Vector(self.ball.pos) + col[2] * d
			v = self.ball.velocity
			v_n = v.normalize()
			normal = col[2]
			m = max((280-v.length2())/100,1)
			v = v - normal * 2 * (normal.dot(v)) * m

			self.ball.velocity = v

		killspace_col_paddle = self.killspace.collide_widget (self.ball)

		# WE DIED!
		if killspace_col_paddle[0]:
			self.sounds["die"].play()
			self.start()

		for w in self.blocks:
			col = w.collide_widget(self.ball)

			if col[0]:
				self.sounds["hit"].play()

				closest = col[1]
				circle = self.ball
				mtd = Vector(circle.pos[0], circle.pos[1]) - closest
				mtd = mtd.normalize()
				pos = closest + mtd * 1.05 * self.ball.size[0]/2
				self.ball.pos = pos

				v = self.ball.velocity
				normal = col[2]
				v = v - normal * 2 * (normal.dot(v))
				self.ball.velocity = v

				self.remove_widget (w)
				self.blocks.remove(w)

				self.score += 5 + 2 * self.level_num

				self.best_score = max(self.score, self.best_score)

				if len(self.blocks) == 0:
					self.n_rings += 1
					self.level_num += 1
					self.ball.setup()
					self.generate_level()

				break

				
class KillSpace(Widget):
	r = 50/2
	r2 = r**r

	def collide_widget(self, wid):
		return circleToCircle (wid, self)

class Paddle(Widget):
	group = "paddle"
	r = 40/2
	r2 = r**r

	def move(self, angle):
		self.canvas.remove_group(self.group)

		r = rect (90/2+self.r-20, angle)

		self.pos = (r.real + cx, r.imag + cy)

	def collide_widget(self, wid):
		return circleToCircle (wid, self)

# Unfortunately, on my PC, the looping is not seamless. :(
class Music(Widget):
	sound = None

	def start(self):
		if self.sound is None:
			self.sound = SoundLoader.load("music.ogg")
			self.sound.volume = 0.8
			self.sound.play()
			self.sound.on_stop = self.sound.play

class CentripetalMenu(Widget):
	def start(self):
		self.t = 0.0

		with self.canvas:
			self.logo = Rectangle(size=(405, 153), pos=(self.size[0]/2 - 405/2, self.size[1]/2 - 153/2 + 150), source='logo.png')
	
	def update(self, dt):
		self.logo.pos = (self.size[0]/2 - 405/2, self.size[1]/2 - 153/2 + 157 + sin(self.t * 3) * 10)

		self.t += dt

class CentripetalRoot(Widget):
	STATE_MENU = 0
	STATE_PLAY = 1
	STATE_WIN = 2
	STATE_LOSE = 3

	def start(self):
		self.state = CentripetalRoot.STATE_MENU

		self.menu = CentripetalMenu()
		self.menu.size = Window.size
		self.add_widget (self.menu)

		self.menu.start()

		Clock.schedule_interval(self.menu.update, 1.0/60.0)

		self.music = Music()
		self.add_widget (self.music)
		self.music.start()

	def start_game(self):
		Clock.unschedule(self.menu.update)

		self.state = CentripetalRoot.STATE_PLAY

		self.remove_widget (self.menu)

		self.game = CentripetalGame()
		self.game.start()

		self.add_widget (self.game)

		Clock.schedule_interval(self.game.update, 1.0/60.0)

	def on_touch_up(self,touch):
		pass
		#if self.state == CentripetalRoot.STATE_MENU:
		#	self.start_game()

Factory.register("Paddle", Paddle)
Factory.register("KillSpace", KillSpace)
Factory.register("Block", Block)
Factory.register("Ball", Ball)
Factory.register("CentripetalGame", CentripetalGame)
Factory.register("CentripetalMenu", CentripetalMenu)
Factory.register("CentripetalRoot", CentripetalRoot)

class CentripetalApp(App):
	icon = 'icon.png'

	def build(self):
		#self.root = FloatLayout()
		#self.grid = None

		#game.start()

		global cx,cy
		cx = Window.center[0]
		cy = Window.center[1]

		root = CentripetalRoot()
		root.size = Window.size
		root.start()
		#Clock.schedule_interval(game.music.loop, 1.0/240.0)

		return root

if __name__ in ('__android__', '__main__'):
	CentripetalApp().run()