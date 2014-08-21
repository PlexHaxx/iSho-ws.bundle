NAME = 'iShows'
BASE_URL = 'http://ishows.tv'

VIDEO_URL = '%s/video?v=%%s' % BASE_URL
SHOWS_URL = '%s/?aj=home&pg=%%d' % BASE_URL
SEASON_URL = '%s/?aj=season&sid=%%s&s=%%s' % BASE_URL
PLAY_VIDEO_URL = '%s/?aj=link&dl=1&v=%%s' % BASE_URL

RE_AMPERSAND = Regex('&(?!amp;)')

ART = 'art-default.jpg'
ICON = 'icon-default.jpg'

####################################################################################################
def Start():

	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME
	DirectoryObject.thumb = R(ICON)

	HTTP.CacheTime = CACHE_1DAY
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (iPad; CPU OS 6_1_3 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B329 Safari/8536.25'
	HTTP.Headers['Referer'] = 'http://ishows.tv/'

####################################################################################################
@handler('/video/ishows', NAME, thumb=ICON, art=ART)
def MainMenu():

	return Shows()

####################################################################################################
@route('/video/ishows/shows/{page}', page=int)
def Shows(page=1):

	oc = ObjectContainer()

	data = HTTP.Request(SHOWS_URL % page, sleep=0.5).content
	data = '<div>%s</div>' % data
	data = RE_AMPERSAND.sub('&amp;', data)
	html = HTML.ElementFromString(data)

	for show in html.xpath('//a[contains(@href, "video?v=")]'):
		title = show.xpath('./div[@class="aar"]/text()')[0]
		thumb = show.xpath('./img/@src')[0]
		video_id = show.get('href').split('?v=')[-1] # We need this to get to a page that lists available seasons
		show_id = thumb.split('?s=')[-1]

		if not thumb.startswith('http://'):
			thumb = '%s%s' % (BASE_URL, thumb)

		oc.add(DirectoryObject(
			key = Callback(Seasons, title=title, thumb=thumb, video_id=video_id, show_id=show_id),
			title = title,
			thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='icon-default.jpg')
		))

	if len(html.xpath('//*[text()="show more"]')) > 0:
		oc.extend(Shows(page=page+1))

	oc.objects.sort(key = lambda obj: obj.title)
	return oc

####################################################################################################
@route('/video/ishows/seasons/{show_id}')
def Seasons(title, thumb, video_id, show_id):

	oc = ObjectContainer(title2=title)

	html = HTML.ElementFromURL(VIDEO_URL % video_id)

	for season in html.xpath('//button[@name="season"]/text()'):
		oc.add(DirectoryObject(
			key = Callback(Episodes, title=season, thumb=thumb, show_id=show_id, season=season.split(' ')[-1]),
			title = season,
			thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='icon-default.jpg')
		))

	return oc

####################################################################################################
@route('/video/ishows/episodes/{show_id}/{season}')
def Episodes(title, thumb, show_id, season):

	oc = ObjectContainer(title2=title)

	data = HTTP.Request(SEASON_URL % (show_id, season)).content
	data = '<div>%s</div>' % data
	data = RE_AMPERSAND.sub('&amp;', data)
	html = HTML.ElementFromString(data)

	for episode in html.xpath('//div[@class="cae"]'):
		video_id = episode.xpath('./div[@class="aag"]/@id')[0].split('-')[-1]
		title = episode.xpath('./div[@class="cac"]/text()')[0]
		title = String.DecodeHTMLEntities(title).replace("\\'", "'")
		index = episode.xpath('.//div[@class="cad"]/text()')[0].split(' ')[-1].split('-')[0]

		oc.add(CreateEpisodeObject(
			show_id = show_id,
			video_id = video_id,
			title = title,
			thumb = thumb,
			season = season,
			index = index
		))

	return oc

####################################################################################################
@route('/video/ishows/createepisodeobject', include_container=bool)
def CreateEpisodeObject(show_id, video_id, title, thumb, season, index, include_container=False):

	episode_obj = EpisodeObject(
		key = Callback(CreateEpisodeObject, show_id=show_id, video_id=video_id, title=title, thumb=thumb, season=season, index=index, include_container=True),
		rating_key = PLAY_VIDEO_URL % video_id,
		title = title,
		thumb = thumb,
		season = int(season),
		index = int(index),
		items = [
			MediaObject(
				parts = [
					PartObject(key=Callback(PlayVideo, show_id=show_id, video_id=video_id))
				],
				container = Container.MP4,
				video_codec = VideoCodec.H264,
				video_resolution = 'sd',
				audio_codec = AudioCodec.AAC,
				audio_channels = 2,
				optimized_for_streaming = True
			)
		]
	)

	if include_container:
		return ObjectContainer(objects=[episode_obj])
	else:
		return episode_obj

####################################################################################################
@indirect
def PlayVideo(show_id, video_id):

	data = HTTP.Request(PLAY_VIDEO_URL % video_id, headers={'Cookie': 'sid=%s' % show_id}).content
	data = '<div>%s</div>' % data
	data = RE_AMPERSAND.sub('&amp;', data)

	html = HTML.ElementFromString(data)
	video_url = html.xpath('//a[contains(@href, "download.php")]/@href')

	if len(video_url) < 1:
		raise Ex.MediaNotAvailable

	return IndirectResponse(VideoClipObject, key=video_url[0])
