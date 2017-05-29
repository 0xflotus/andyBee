from lxml import etree
from app import geocache_db
from geocache_model_sql import Cache, Cacher, CacheType, CacheContainer, CacheCountry, CacheState, Waypoint, WaypointSym, WaypointType, Log, LogType, Attribute
import re
import datetime

GPX_NS = "http://www.topografix.com/GPX/1/0"
GPX = "{%s}" % GPX_NS
GS_NS = "http://www.groundspeak.com/cache/1/0/1"
GS = "{%s}" % GS_NS
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XSI = "{%s}" % XSI_NS

latmin = 0
latmax = 0
lonmin = 0
lonmax = 0

def wpt_to_xml(parent, waypoint, data):
    data['latmin'] = min(data['latmin'], waypoint.lat)
    data['latmax'] = max(data['latmax'], waypoint.lat)
    data['lonmin'] = min(data['lonmin'], waypoint.lon)
    data['lonmax'] = max(data['lonmax'], waypoint.lon)
    w_wpt = subnode(parent, GPX+"wpt", attrib={'lat': str(waypoint.lat), 'lon': str(waypoint.lon)})
    subnode(w_wpt, GPX+"time", text=waypoint.time)
    subnode(w_wpt, GPX+"name", text=waypoint.name)
    subnode(w_wpt, GPX+"cmt", text=waypoint.cmt)
    subnode(w_wpt, GPX+"desc", text=waypoint.desc)
    subnode(w_wpt, GPX+"url", text=waypoint.url)
    subnode(w_wpt, GPX+"urlname", text=waypoint.urlname)
    subnode(w_wpt, GPX+"sym", text=waypoint.sym.name)
    subnode(w_wpt, GPX+"type", text=waypoint.type.name)
    return w_wpt

def geocache_to_xml(parent, geocache, data):
    wpt_node = wpt_to_xml(parent, geocache.waypoint, data)
    cache_node = subnode(wpt_node, GS+"cache", nsmap={'groundspeak':GS_NS}, 
            attrib={
                'id': str(geocache.id),
                'available': "True" if geocache.available else "False",
                'archived': "True" if geocache.archived else "False"})
    subnode(cache_node, GS+"name", text=geocache.name)
    subnode(cache_node, GS+"placed_by", text=geocache.placed_by)
    subnode(cache_node, GS+"owner", text=geocache.owner.name, attrib={'id': str(geocache.owner_id)})
    subnode(cache_node, GS+"type", text=geocache.type.name)
    subnode(cache_node, GS+"container", text=geocache.container.name)
    if len(geocache.attributes):
        attr_node = subnode(cache_node, GS+"attributes")
        for attribute in geocache.attributes:
            subnode(attr_node, GS+"attribute", text=attribute.name, 
                    attrib={
                        'id': str(attribute.gc_id),
                        'inc': "1" if attribute.inc else "0"})
    subnode(cache_node, GS+"difficulty", text=re.sub('\.0','', str(geocache.difficulty)))
    subnode(cache_node, GS+"terrain", text=re.sub('\.0','',str(geocache.terrain)))
    subnode(cache_node, GS+"country", text=geocache.country.name)
    subnode(cache_node, GS+"state", text=geocache.state.name)
    subnode(cache_node, GS+"short_description", text=geocache.short_desc,
            attrib={'html': "True" if geocache.short_html else "False"})
    subnode(cache_node, GS+"long_description", text=geocache.long_desc,
            attrib={'html': "True" if geocache.long_html else "False"})
    subnode(cache_node, GS+"encoded_hints", text=geocache.encoded_hints)
    if len(geocache.logs) and (data['max_logs'] > 0):
        sort_logs = sorted(geocache.logs, key=lambda log: log.date)
        logs_node = subnode(cache_node, GS+"logs")
        for log in sort_logs[0:data['max_logs']]:
            log_node = subnode(logs_node, GS+"log", attrib={'id': str(log.id)})
            subnode(log_node, GS+"date", text=log.date)
            subnode(log_node, GS+"type", text=log.type.name)
            subnode(log_node, GS+"finder", text=log.finder.name, attrib={'id': str(log.finder_id)})
            subnode(log_node, GS+"text", text=log.text, attrib={'encoded': 'True' if log.text_encoded else 'False'})
    if data['waypoints']:
        wpts = geocache_db.session.query(Waypoint).filter_by(gc_code=geocache.waypoint.name).all()
        for wpt in wpts:
            if wpt.cache_id is None:
                wpt_to_xml(parent, wpt, data)


def subnode(parent, tag_name, text=None, attrib=None, nsmap=None):
    node = etree.SubElement(parent, tag_name, nsmap=nsmap)
    if text is not None:
        node.text = text
    if attrib is not None:
        for name, val in attrib.iteritems():
            node.attrib[name] = val
    return node


def export_gpx(data):
    data['latmin'] = 1000.0
    data['latmax'] = -1000.0
    data['lonmin'] = 1000.0
    data['lonmax'] = -1000.0

    root = etree.Element(GPX+"gpx", nsmap={None:GPX_NS, "xsi":XSI_NS})
    root.attrib["version"] = "1.0"
    root.attrib["creator"] = "geodb, all rights reserved"
    root.attrib[XSI+"schemaLocation"] = "{} {}/gpx.xsd {} {}/cache.xsd".format(GPX_NS,GPX_NS,GS_NS,GS_NS)

    subnode(root, GPX+"name"   , text="Cache Listing Generated by andiBee")                        
    subnode(root, GPX+"desc"   , text="This is an individual list of geocaches generated by andiBee.")
    subnode(root, GPX+"author" , text="Hi, that's me: Jens Guballa")                             
    subnode(root, GPX+"email"  , text="andiBee@guballa.de")                                        
    subnode(root, GPX+"url"    , text="http://www.guballa.de")                                   
    subnode(root, GPX+"urlname", text="Geocaching. What else?")                                  
    subnode(root, GPX+"time"   , text=datetime.datetime.now().isoformat())                       
    subnode(root, GPX+"keyword", text="cache, geocache")                                         
    bounds = subnode(root, GPX+"bounds")                                                                  

    for id in data['list']:
        geocache = geocache_db.session.query(Cache).get(id)
        geocache_to_xml(root, geocache, data)

    bounds.attrib['minlat'] = str(data['latmin'])
    bounds.attrib['minlon'] = str(data['lonmin'])
    bounds.attrib['maxlat'] = str(data['latmax'])
    bounds.attrib['maxlon'] = str(data['lonmax'])

    et = etree.ElementTree(root)
    return etree.tostring(et, pretty_print=True, encoding="UTF-8", xml_declaration=True)

def import_gpx(filename):
    try:
        tree = etree.parse(filename)
    except:
        return
    gpx = tree.getroot()
    if gpx.tag == GPX+"gpx":
        for node in gpx:
            if node.tag == GPX+"wpt":
                parse_wpt(node)
        geocache_db.commit()

def parse_wpt(node):
    cache = None
    wpt = Waypoint()
    wpt.lat = float(node.get("lat"))
    wpt.lon = float(node.get("lon"))
    for child in node:
        if child.tag == GPX+"time":
            wpt.time = child.text
        elif child.tag == GPX+"name":
            wpt.name = child.text
            wpt.gc_code = re.sub('^..', 'GC', wpt.name)
        elif child.tag == GPX+"desc":
            wpt.descr = child.text
        elif child.tag == GPX+"url":
            wpt.url = child.text
        elif child.tag == GPX+"urlname":
            wpt.urlname = child.text
        elif child.tag == GPX+"sym":
            wpt.sym_id = geocache_db.unique_factory(WaypointSym, name=child.text)
        elif child.tag == GPX+"type":
            wpt.type_id = geocache_db.unique_factory(WaypointType, name=child.text)
        elif child.tag == GPX+"cmt":
            wpt.cmt = child.text
        elif child.tag == GS+"cache":
            cache = parse_cache(child)
            wpt.cache_id = cache.id
    if cache is not None:
        # copy some values from the waypoint, so that join statements
        # can be avoided
        cache.lat = wpt.lat
        cache.lon = wpt.lon
        cache.gc_id = wpt.name
        stmt, paras = cache.insert()
        geocache_db.execute(stmt, paras)

    stmt, paras = wpt.insert()
    geocache_db.execute(stmt, paras)

def parse_cache(node):
    logs = []
    cache = Cache()
    cache.id = int(node.get("id"))
    cache.available = (node.get("available") == "True")
    cache.archived = (node.get("archived") == "True")
    for child in node:
        if child.tag == GS+"name":
            cache.name = child.text
        elif child.tag == GS+"placed_by":
            cache.placed_by = child.text
        elif child.tag == GS+"owner":
            cache.owner_id = geocache_db.unique_factory(Cacher, id=child.get("id") , name=child.text)
        elif child.tag == GS+"type":
            cache.type_id = geocache_db.unique_factory(CacheType, name=child.text)
        elif child.tag == GS+"container":
            cache.container_id = geocache_db.unique_factory(CacheContainer, name=child.text)
        elif child.tag == GS+"difficulty":
            cache.difficulty = float(child.text)
        elif child.tag == GS+"terrain":
            cache.terrain = float(child.text)
        elif child.tag == GS+"country":
            cache.country_id = geocache_db.unique_factory(CacheCountry, name=child.text)
        elif child.tag == GS+"state":
            cache.state_id = geocache_db.unique_factory(CacheState, name=child.text)
        elif child.tag == GS+"short_description":
            cache.short_desc = child.text
            cache.short_html = (child.get("html") == "True")
        elif child.tag == GS+"long_description":
            cache.long_desc = child.text
            cache.long_html = (child.get("html") == "True")
        elif child.tag == GS+"encoded_hints":
            cache.encoded_hints = child.text
        elif child.tag == GS+"attributes":
            for node_attr in child:
                if node_attr.tag == GS+"attribute":
                    parse_attribute(node_attr, cache.id)
#                    cache.attributes.append(parse_attribute(node_attr))
        elif child.tag == GS+"logs":
            for node_log in child:
                if node_log.tag == GS+"log":
                    logs.append(parse_log(node_log, cache.id))

    # Now return the log types of the 5 latest logs as a string
    sorted_logs = sorted(logs, key=lambda x: x.date, reverse=True)
    cache.last_logs = ";".join([l.type for l in sorted_logs[:5]])

    return cache

def parse_attribute(node, cache_id):
    id = geocache_db.unique_factory(Attribute,  
            gc_id=int(node.get("id")),
            inc=(node.get("inc") == "1"),
            name=node.text)
    geocache_db.execute('INSERT INTO cache_to_attribute (cache_id, attribute_id) VALUES (?,?)', (cache_id, id))


def parse_log(node, cache_id):
    type_txt = None
    log = Log()
    log.id = int(node.get("id"))
    log.cache_id = cache_id
    for log_node in node:
        if log_node.tag == GS+"date":
            log.date = log_node.text
        elif log_node.tag == GS+"type":
            log.type_id = geocache_db.unique_factory(LogType, name=log_node.text)
            type_txt = log_node.text
        elif log_node.tag == GS+"finder":
            log.finder_id = geocache_db.unique_factory(Cacher, id=log_node.get("id"), name=log_node.text)
        elif log_node.tag == GS+"text":
            log.text = log_node.text
            log.text_encoded = (log_node.get("encoded") == "True")
        elif log_node.tag == GS+"log_wpt":
            log.lat = float(log_node.get("lat"))
            log.lon = float(log_node.get("lon"))

    stmt, paras = log.insert()
    geocache_db.execute(stmt, paras)
    log.type = type_txt    
    return log

