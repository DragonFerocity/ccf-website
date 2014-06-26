from google.appengine.ext import webapp
import base64
import logging
from webapp2_extras import jinja2
from xml.dom import minidom, Node
from xml.dom.minidom import getDOMImplementation,parseString
import httplib
from scripts.gaesettings import gaesettings


class DotDict(dict):
    """A dot-accessable dict-like object for accessing the checkout XML"""
    def __getattr__(self, attr):
        if attr in self:
            return self.get(attr, None)
        else:
            raise AttributeError("no attr %s" % (attr))
    @property
    def items(self):
        """more convient items access"""
        items_list = self['items'].get('item',[])
        if not isinstance(items_list, list):
            items_list = [items_list]
        return items_list
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

def node_to_dotdict(self):
    """The google XML format is very simple so we can easily convert the
    whole thing into a big dict. this function returns a DotDict
    repeated values are converted to lists"""
    d = DotDict()
    for node in self.childNodes:
        if node.nodeType == Node.TEXT_NODE and node.nodeValue.strip():
            return node.nodeValue
        elif node.nodeType == Node.ELEMENT_NODE:
            name = node.nodeName.replace('-','_')
            value = node_to_dotdict(node)
            if name in d and isinstance(getattr(d,name),(dict,basestring,list)):
                if isinstance(d[name],list):
                    d[name].append(value)
                else:
                    d[name] = [d[name], value]
            else:
                d[name] = value
            # special case for currency attribute
            # currency is prettymuch the only attribute
            # used. it is converted into TAGNAME_ATTRNAME
            cur = node.getAttribute("currency")
            if cur:
                d[name+"_currency"] = cur
    return d

def xml_to_dotdict(xmlstr):
    dom = minidom.parseString(xmlstr)
    return node_to_dotdict(dom.documentElement)

class Error(Exception):
    """Base class for exceptions in this module."""

class IgnoreNotification(Error):
    """Base class for exceptions raised to ackknowledge
    by not do anything with a notification"""

def get_list_from_value(notification_value):
    "Checks to see if value in notification dict is a list or unicode. Returns list of value(s) as integers."
    if type(notification_value) == list:
        return [ int(x) for x in notification_value ]
    else: return [int(notification_value)]


class Client(object):
    def __init__(self, merchant_id, merchant_key, sandbox=False, currency="USD"):
        self.merchant_id = merchant_id
        self.merchant_key = merchant_key
        self.sandbox = sandbox
        self.currency = currency
        self.urls = { "donation-xml":              "/api/checkout/v2/merchantCheckout/Donations/{merchant_id}".format(merchant_id=self.merchant_id),
                      "donation-order_processing": "/api/checkout/v2/request/Donations/{merchant_id}".format(merchant_id=self.merchant_id),
                     #"xml order":                 "/api/checkout/v2/request/Merchant/{merchant_id}".format(merchant_id=self.merchant_id),
                    }
        if sandbox:
            self.checkout_server = "sandbox.google.com"
            for url_name in self.urls:
                self.urls[url_name] = "/checkout" + self.urls[url_name]
        else:
            self.checkout_server = "checkout.google.com"

    def send_request(self, xml, url_name):
        headers = {
            "Content-type": "application/xml; charset=UTF-8",
            "Accept": "application/xml; charset=UTF-8",
            "Authorization": self.get_authorization()}
        conn = httplib.HTTPSConnection(self.checkout_server)
        conn.request("POST", self.urls[url_name], xml, headers)
        response = conn.getresponse()
        body = response.read()
        doc = parseString(body).documentElement
        # handle error responses by raising them as exceptions
        if response.status != 200:
            errs = doc.getElementsByTagName("error-message")
            errmsg = ""
            for e in errs:
                errmsg += e.firstChild.data.encode("ascii", "ignore") + " "
            raise Exception("google checkout: " + errmsg)
        return doc

    def get_authorization(self):
        return "Basic " + base64.b64encode(self.merchant_id + ":" + self.merchant_key)

    def create_new_order(self, **kwargs):
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader('scripts/donations/google'))
        template = env.get_template('google_checkout.xml')
        xml = template.render(**kwargs)
        doc = self.send_request(xml, url_name="donation-xml")

        return node_to_dotdict(doc)['redirect_url']

    def existing_order(self, order_number):
        return Order(order_number=order_number,
                     merchant_id=self.merchant_id, merchant_key=self.merchant_key,
                     sandbox=self.sandbox, currency=self.currency)


class NotificationHandler(webapp.RequestHandler):
    """A base RequestHandler handler class for implimenting the google-checkout notification API.

    Create a webapp handler by subclassing the NotificationHandler defining a merchant_details
    method and overriding any notification methods you wish to use:

        class MyNotificationHandler(NotificationHandler)

            def merchant_details():
                "return a tuple of your merchant details"
                return (your_id, your_key)

            def new_order(self):
                logging.info("got a new order notification", self.notification)

    By default NotificationHandler silently accepts all notifications and leaves a
    message in the log. It expects that you will overide one or more of the following methods
    in your Handler:

        class MyNotificationHandler(NotificationHandler)

            new_order(self):
                "Do something with the new-order-notification"

            def risk_information(self):
                "Do something with the risk-information-notification"

            def order_state_change(self):
                "Do something with the order-state-change-notification"

            def charge_amount(self):
                "Do something with the charge-amount-notification"

    Within the context of a NotificationHandler self.notification contains a dict-like object
    with all the notification values that can be found at:
    http://code.google.com/apis/checkout/developer/Google_Checkout_XML_API_Notification_API.html#Types_of_Notifications

    The values in self.notifications are pythonized by converting "-" to "_". So 'order-summary' becomes 'order_summary'
    This allows you to access the values via dot-notation. For example:

        self.notification.order_summary.google_order_number # contains the order reference

    As a full example, if we have a simple Order model to store our new order details
    we could then make a notification handler

        class Order(db.Model):
            amount = db.StringProperty()
            paid = db.StringProperty()
            name = db.StringProperty()
            email = db.StringProperty()
            address_line_1 = StringProperty()
            city = StringProperty()
            postcode = StringProperty()
            phone = StringProperty()
            items = db.StringListProperty()

        class MyNotificationHandler(NotificationHandler):
            "An example notifcation handle"

            def merchant_details():
                "return a tuple of your merchant details"
                return ("12345678910", "Axoiuyfq2309230f9u2gf")

            def new_order(self):
                "Create an order for the incoming order notification"
                # first check if we already created this order (maybe the notification can in twice
                order = Order.all().get_by_key_name(self.notification.google_order_number)
                if order:
                    return
                # otherwise create an order
                order = Order(
                    key_name       = self.notification.google_order_number,
                    name           = self.notification.buyer_shipping_address.contact_name,
                    email          = self.notification.buyer_shipping_address.email,
                    address_line_1 = self.notification.buyer_shipping_address.address1,
                    city           = self.notification.buyer_shipping_address.city,
                    postcode       = self.notification.buyer_shipping_address.postal_code,
                    amount         = self.notification.order_total,
                    phone          = self.notification.buyer_shipping_address.phone)
                # record each item in the order
                for item in self.notification.shopping_cart.items:
                    order.items.append( item.item_name )
                order.put()

            def charge_amount(self):
                "Mark a previous order as paid"
                order = Order.all().get_by_key_name(self.notification.google_order_number)
                order.paid = True
                order.put()

    any exceptions raised during execution of the notification will result in the notification being resent
    from google-checkout.

    raise IgnoreNotification if you wish to raise an exception and also return send an OK ackknowledgement to
    google-checkout to prevent re-sending.
    """

    def merchant_details(self):
        "Return tuple of (merchant_id,merchant_key)"
        raise Error("Missing merchant details. define a %s.merchant_details method to return a tuple of (merchant_id,merchant_key)", self.__class__.__name__)

    def _parse_notification(self):
        "All google notifications are parsed and categorized by type."
        dom = minidom.parseString(self.request.body)
        # store the notification type
        self.notification_type = dom.childNodes[0].localName
        # convert the xml to a more python friendly format (a dict with dot-access)
        self.notification = node_to_dotdict(dom.documentElement)
        # get the serial number
        try:
            self.notification_serial_number = dom.childNodes[0].attributes["serial-number"].value
        except KeyError:
            logging.error("GoogleNotification: notification body did not contain a serial-number field")
            raise
        # create a RemoteOrder (for interacting with Order Processing API)
        self.remote_order = self._remote_order()

    def _handshake(self):
        "Acknowledge receipt of notification."
        doc = minidom.Document()
        ack = doc.createElement("notification-acknowledgment")
        ack.setAttribute("xmlns","http://checkout.google.com/schema/2")
        ack.setAttribute("serial-number", self.notification_serial_number)
        doc.appendChild(ack)
        # return full acknowledgment
        self.response.headers['Content-Type'] = 'text/xml'
        self.response.out.write( doc.toxml(encoding="utf-8") )

    def _check_request(self):
        "Check to ensure valid Google notification."
        if not self.request.headers.get('Authorization'):
            logging.error("GoogleNotification: incoming notification had no Authorization header")
            return self.error(401)
        #get the Authorization string from the Google POST header
        auth_string = self.request.headers.get('Authorization')
        #decode the Authorization string and remove Basic portion
        plain_string = base64.b64decode(auth_string.lstrip('Basic '))
        #split the decoded string at the ':'
        merchant_id, merchant_key = plain_string.split(':')
        # check credentials
        our_merchant_id,our_merchant_key = self.merchant_details()
        if merchant_id != our_merchant_id or merchant_key != our_merchant_key:
            logging.error("GoogleNotification: incoming notification had unexpected merchant id and/or key")
            return self.error(401)
        # check body exits
        if not self.request.body:
            logging.error("GoogleNotification: incoming notification had no request body")
            return self.error(400)
        # everything looks ok
        return True

    def _remote_order(self):
        """
        returns an instance of the googlecheckout.Client Order for the
        currently related order notification.

        You should not need to call this method directly and use the property
        self.remote_order insted

        You can use this to interact with the checkout orders via the
        Order Processing API

        For example if you wanted to automatically ship all orders under $10
        but instantly cancel all orders over $50 you might do something like:

            class MyNotificationHandler(NotificationHandler):
                "An example notifcation handle"

                def merchant_details():
                    "return a tuple of your merchant details"
                    return ("12345678910", "Axoiuyfq2309230f9u2gf")

                def new_order(self):
                    if int(self.notification.order_total) < 10:
                        self.remote_order.charge_and_ship(self.notification.order_total)
                    elif int(self.notification.order_total) > 3000:
                        self.remote_order.cancel()
        """
        mid,mkey = self.merchant_details()
        try:
            cur = self.notification.order_summary.order_total_currency
        except AttributeError:
            cur = None
        RemoteOrder = Client(mid, mkey, currency=cur if cur else "USD")
        return RemoteOrder(self.notification.google_order_number)

    def new_order(self):
        self.unhandled_notification()

    def risk_information(self):
        self.unhandled_notification()

    def order_state_change(self):
        self.unhandled_notification()

    def charge_amount(self):
        self.unhandled_notification()

    def chargeback_amount(self):
        self.unhandled_notification()

    def refund_amount(self):
        self.unhandled_notification()

    def authorization_amount(self):
        self.unhandled_notification()

    def unhandled_notification(self):
        raise IgnoreNotification("GoogleNotification: %s received but ignored" %  self.notification_type)

    def _process_notification(self):
        "call the apropriate method for each notification type"
        if self.notification_type == 'new-order-notification': #new order
            self.new_order()
        elif self.notification_type == 'risk-information-notification':
            self.risk_information()
        elif self.notification_type == 'order-state-change-notification':
            self.order_state_change()
        elif self.notification_type == 'charge-amount-notification':
            self.charge_amount()
        elif self.notification_type == 'authorization-amount-notification':
            self.authorization_amount()
        elif self.notification_type == 'refund-amount-notification':
            self.refund_amount()
        elif self.notification_type == 'chargeback-amount-notification':
            self.chargeback_amount()
        else: #all other notifications are ignored
            self.unhandled_notification()

    def post(self):
        if not self._check_request():
            logging.error("GoogleNotification: invalid")
            return
        # parse/init notification request
        self._parse_notification()
        # try to call process notification method
        try:
            self._process_notification()
        except IgnoreNotification, e:
            # if IgnoreNotification is raised, the handshake will be completed
            # so google will not retry the notifcation in the future. all handler
            # methods raise this by default
            logging.info(str(e))
        self._handshake()


# order processing api:
class Order(object):
    def __init__(self, order_number):
        self.merchant_id = merchant_id
        self.merchant_key = merchant_key
        self.order_number = order_number
        self.currency = currency

    def _doc(self, tag):
        doc = getDOMImplementation().createDocument(None, tag, None)
        # set ns
        doc.documentElement.setAttribute("xmlns", "http://checkout.google.com/schema/2")
        # set order id
        doc.documentElement.setAttribute("google-order-number", self.order_number)
        return doc

    def authorize(self):
        """
        instructs Google Checkout to explicitly reauthorize a customer's
        credit card for the uncharged balance of an order to verify that
        funds for the order are available. You may issue an authorize command
        for an order that is in either CHARGEABLE or CHARGED states (You could
        reauthorize an order that had been partially charged.)
        """
        # WARNING: you may be charged $0.30 for this call
        doc = self._doc("authorize-order")
        # send xml msg to google checkout
        self._request( doc.toxml("utf-8") )

    def cancel(self, reason="no reason given", comment=""):
        """
        instructs Google Checkout to cancel a particular order. If the customer
        has already been charged, you must refund the customer's money before you
        can cancel the order. You may only issue a "cancel" command for an order that
        is in either CHARGEABLE or PAYMENT_DECLINED state
        """
        doc = self._doc("cancel-order")
        # set reason
        el = doc.createElement("reason")
        el.appendChild( doc.createTextNode(str(reason)) )
        doc.documentElement.appendChild(el)
        # set comment
        if comment:
            el = doc.createElement("comment")
            el.appendChild( doc.createTextNode(str(comment)) )
            doc.documentElement.appendChild(el)
        # send xml msg to google checkout
        self._request( doc.toxml("utf-8") )

    def refund(self, reason, amount=None, comment=""):
        """
        instructs Google Checkout to refund the buyer for a particular order.
        You may issue a "refund" for orders in CHARGED state.
        """
        doc = self._doc("refund-order")
        # set amount to refund
        if amount is not None:
            el = doc.createElement("amount")
            el.setAttribute("currency", self.currency)
            el.appendChild( doc.createTextNode(str(amount)) )
            doc.documentElement.appendChild(el)
        # set reason
        el = doc.createElement("reason")
        el.appendChild( doc.createTextNode(str(reason)) )
        doc.documentElement.appendChild(el)
        # set comment
        if comment:
            el = doc.createElement("comment")
            el.appendChild( doc.createTextNode(str(comment)) )
            doc.documentElement.appendChild(el)
        # send xml msg to google checkout
        self._request( doc.toxml("utf-8") )

    def charge_and_ship(self, amount=None, carrier=None, carrier_id=None):
        """
        instructs Google Checkout to charge the buyer for a particular
        order. After an order reaches the CHARGEABLE order state, you have seven
        days (168 hours) to capture funds by issuing a <charge-and-ship-order>
        command. You may issue a <charge-and-ship-order> command for orders
        that are in CHARGEABLE or CHARGED (if the order has only been partially charged)
        states
        """
        doc = self._doc("charge-and-ship-order")
        # set amount to charge (or leave blank for full)
        if amount is not None:
            el = doc.createElement("amount")
            el.setAttribute("currency", self.currency)
            el.appendChild( doc.createTextNode(str(amount)) )
            doc.documentElement.appendChild(el)
        # set tracking data (if given)
        if carrier is not None or carrier_id is not None:
            tel = doc.createElement("tracking-data")
            # set carrier (if given)
            if carrier is not None:
                cel = doc.createElement("carrier")
                cel.appendChild( doc.createTextNode(carrier) )
                tel.appendChild(cel)
            # set tracking id if given along with carrier
            if carrier_id is not None:
                nel = doc.createElement("tracking-number")
                nel.appendChild( doc.createTextNode(carrier_id) )
                tel.appendChild(nel)
            # add item to list
            el = doc.createElement("tracking-data-list")
            el.appendChild(tel)
            doc.documentElement.appendChild(el)
        # send xml msg to google checkout
        self._request( doc.toxml("utf-8") )


if gaesettings.google_checkout_use_sandbox:
    client = Client(gaesettings.google_checkout_sandbox_merchant_id, gaesettings.google_checkout_sandbox_merchant_key, sandbox=True)
else:
    client = Client(gaesettings.google_checkout_merchant_id, gaesettings.google_checkout_merchant_key, sandbox=False)
