"""Bundled Qt framework reference entries for nexcpp.

All content in this module is original work, released under the MIT License
along with the rest of nexcpp. Qt type names, signal/slot signatures, and
macro names are facts about the Qt public API and are not copyrightable. All
prose descriptions and code examples in this file are original; they do not
derive from upstream documentation or other copyrighted sources.
"""

from __future__ import annotations

from ._common import e

_URL = "https://doc.qt.io/qt-6/"


def _qt(symbol: str, *, slug: str, brief: str, header: str, signature: str = "", example: str = "") -> object:
    return e(
        symbol,
        header=header,
        since="",
        brief=brief,
        signature=signature,
        example=example,
        url=_URL + slug + ".html",
        source="qt",
    )


ENTRIES = [
    _qt(
        "QObject",
        slug="qobject",
        brief="Base class for any Qt type that participates in the meta-object system: signals, slots, properties, and dynamic introspection.",
        header="<QObject>",
        signature="class QObject;",
        example="class Worker : public QObject {\n  Q_OBJECT\n};",
    ),
    _qt(
        "QWidget",
        slug="qwidget",
        brief="Base class for all visible UI elements in the Qt Widgets module. Handles paint events, layouts, and input.",
        header="<QWidget>",
        signature="class QWidget : public QObject, public QPaintDevice;",
        example="QWidget w;\nw.resize(400, 300);\nw.show();",
    ),
    _qt(
        "QApplication",
        slug="qapplication",
        brief="Event loop driver for desktop GUI applications. Exactly one instance must exist before any widget is constructed.",
        header="<QApplication>",
        signature="class QApplication : public QGuiApplication;",
        example="QApplication app(argc, argv);\nQWidget w;\nw.show();\nreturn app.exec();",
    ),
    _qt(
        "QGuiApplication",
        slug="qguiapplication",
        brief="Application object for Qt programs that use Qt Quick or raw QWindow but not the Widgets module.",
        header="<QGuiApplication>",
        signature="class QGuiApplication : public QCoreApplication;",
        example="QGuiApplication app(argc, argv);\nreturn app.exec();",
    ),
    _qt(
        "QString",
        slug="qstring",
        brief="Implicitly shared, UTF-16 string class. Conversions to and from std::string are explicit.",
        header="<QString>",
        signature="class QString;",
        example="QString s = QStringLiteral(\"hello\");\ns.append(\" world\");",
    ),
    _qt(
        "QByteArray",
        slug="qbytearray",
        brief="Implicitly shared sequence of bytes. Used for binary I/O, hashing, and encoding conversions.",
        header="<QByteArray>",
        signature="class QByteArray;",
        example="QByteArray b = \"hi\";\nb.append('!');",
    ),
    _qt(
        "QVector",
        slug="qvector",
        brief="Sequence container similar to QList. In Qt 6, QVector is an alias for QList.",
        header="<QVector>",
        signature="template<class T> using QVector = QList<T>;",
        example="QVector<int> v{1, 2, 3};\nv.append(4);",
    ),
    _qt(
        "QList",
        slug="qlist",
        brief="Implicitly shared, contiguous list. The primary general-purpose Qt sequence container.",
        header="<QList>",
        signature="template<class T> class QList;",
        example="QList<QString> xs;\nxs.append(QStringLiteral(\"x\"));",
    ),
    _qt(
        "QHash",
        slug="qhash",
        brief="Implicitly shared hash table. Average O(1) lookup, no key ordering.",
        header="<QHash>",
        signature="template<class K, class V> class QHash;",
        example="QHash<QString, int> h;\nh.insert(\"x\", 1);",
    ),
    _qt(
        "QMap",
        slug="qmap",
        brief="Sorted associative container backed by a balanced tree. Use QHash when ordering is not needed.",
        header="<QMap>",
        signature="template<class K, class V> class QMap;",
        example="QMap<QString, int> m;\nm.insert(\"a\", 1);",
    ),
    _qt(
        "QFile",
        slug="qfile",
        brief="File I/O device. Inherits from QIODevice so the same read/write interface is shared with sockets and processes.",
        header="<QFile>",
        signature="class QFile : public QFileDevice;",
        example="QFile f(\"data.txt\");\nif (f.open(QIODevice::ReadOnly)) {}",
    ),
    _qt(
        "QTextStream",
        slug="qtextstream",
        brief="Buffered text stream over any QIODevice or QString, with encoding handling.",
        header="<QTextStream>",
        signature="class QTextStream;",
        example="QFile f(\"out.txt\");\nf.open(QIODevice::WriteOnly);\nQTextStream(&f) << \"hi\";",
    ),
    _qt(
        "QNetworkAccessManager",
        slug="qnetworkaccessmanager",
        brief="High-level HTTP client. Issues GET/POST/PUT requests and returns QNetworkReply objects.",
        header="<QNetworkAccessManager>",
        signature="class QNetworkAccessManager : public QObject;",
        example="QNetworkAccessManager nm;\nauto* r = nm.get(QNetworkRequest(QUrl(\"https://example.com\")));",
    ),
    _qt(
        "QThread",
        slug="qthread",
        brief="Object-affine wrapper around an OS thread. Use it together with QObject::moveToThread to run code in another thread.",
        header="<QThread>",
        signature="class QThread : public QObject;",
        example="QThread t;\nworker->moveToThread(&t);\nt.start();",
    ),
    _qt(
        "QtConnect",
        slug="signalsandslots",
        brief="Type-safe connection between a signal and a slot or functor. Captures sender/receiver lifetime to disconnect automatically.",
        header="<QObject>",
        signature="static QMetaObject::Connection QObject::connect(sender, signal, receiver, slot);",
        example="QObject::connect(&button, &QPushButton::clicked, this, &Form::onClick);",
    ),
    _qt(
        "Q_OBJECT",
        slug="qobject",
        brief="Macro placed in the private section of a QObject subclass that enables signals, slots, properties, and runtime type info via moc.",
        header="<QObject>",
        signature="#define Q_OBJECT /* moc-expanded */",
        example="class Form : public QWidget {\n  Q_OBJECT\n};",
    ),
    _qt(
        "qobject_cast",
        slug="qobject",
        brief="Compile-time-safe down-cast for QObject* that uses Qt's meta-object system instead of RTTI.",
        header="<QObject>",
        signature="template<class T> T qobject_cast(QObject* obj);",
        example="if (auto* b = qobject_cast<QPushButton*>(sender())) {}",
    ),
    _qt(
        "QML",
        slug="qmlapplications",
        brief="Declarative UI language for Qt Quick. Files use a JavaScript-like syntax; types resolve to QObject subclasses at runtime.",
        header="QML (.qml files)",
        signature="import QtQuick 2.15\nItem { ... }",
        example="Rectangle {\n  width: 200; height: 100\n  color: \"red\"\n}",
    ),
]
