"""Bundled LLVM and Clang reference entries for nexcpp.

All content in this module is original work, released under the MIT License
along with the rest of nexcpp. LLVM and Clang class names and namespace
layout are facts about the public LLVM/Clang APIs and are not copyrightable.
All prose descriptions and code examples in this file are original; they do
not derive from upstream documentation or other copyrighted sources.
"""

from __future__ import annotations

from ._common import e

_LLVM = "https://llvm.org/doxygen/"
_CLANG = "https://clang.llvm.org/doxygen/"


ENTRIES = [
    e(
        "clang::ASTContext",
        header="<clang/AST/ASTContext.h>",
        since="",
        brief="Owns the AST of a translation unit: type system, source manager, identifier table, and built-in declarations.",
        signature="class ASTContext;",
        example="auto& ctx = compiler.getASTContext();\nauto& sm = ctx.getSourceManager();",
        url=_CLANG + "classclang_1_1ASTContext.html",
        source="llvm",
    ),
    e(
        "clang::CompilerInstance",
        header="<clang/Frontend/CompilerInstance.h>",
        since="",
        brief="Coordinates the compilation pipeline: diagnostics, preprocessor, source manager, AST, code generation.",
        signature="class CompilerInstance;",
        example="clang::CompilerInstance ci;\nci.createDiagnostics();",
        url=_CLANG + "classclang_1_1CompilerInstance.html",
        source="llvm",
    ),
    e(
        "clang::tooling::ClangTool",
        header="<clang/Tooling/Tooling.h>",
        since="",
        brief="Convenience driver that runs a FrontendAction over a set of source files using a CompilationDatabase.",
        signature="class ClangTool;",
        example="clang::tooling::ClangTool tool(db, files);\nint rc = tool.run(factory.get());",
        url=_CLANG + "classclang_1_1tooling_1_1ClangTool.html",
        source="llvm",
    ),
    e(
        "clang::Rewriter",
        header="<clang/Rewrite/Core/Rewriter.h>",
        since="",
        brief="Mutates source ranges in-place while preserving unrelated text. Used to implement refactoring tools.",
        signature="class Rewriter;",
        example="rewriter.ReplaceText(range, \"new_name\");",
        url=_CLANG + "classclang_1_1Rewriter.html",
        source="llvm",
    ),
    e(
        "clang::SourceManager",
        header="<clang/Basic/SourceManager.h>",
        since="",
        brief="Maps SourceLocations back to files, lines, and columns. Owns the loaded source buffers.",
        signature="class SourceManager;",
        example="auto loc = sm.getSpellingLoc(tok.getLocation());",
        url=_CLANG + "classclang_1_1SourceManager.html",
        source="llvm",
    ),
    e(
        "clang::DiagnosticsEngine",
        header="<clang/Basic/Diagnostic.h>",
        since="",
        brief="Reports compiler diagnostics. Tools emit warnings and errors through this object so they appear in standard tooling output.",
        signature="class DiagnosticsEngine;",
        example="diag.Report(loc, diag.getCustomDiagID(level, \"message\"));",
        url=_CLANG + "classclang_1_1DiagnosticsEngine.html",
        source="llvm",
    ),
    e(
        "clang::ast_matchers",
        header="<clang/ASTMatchers/ASTMatchers.h>",
        since="",
        brief="DSL of composable matchers for finding AST nodes. Pair with MatchFinder to invoke a callback on each hit.",
        signature="namespace clang::ast_matchers;",
        example="auto m = functionDecl(hasName(\"main\"));",
        url=_CLANG + "classclang_1_1ast__matchers_1_1MatchFinder.html",
        source="llvm",
    ),
    e(
        "clang::tooling::CompilationDatabase",
        header="<clang/Tooling/CompilationDatabase.h>",
        since="",
        brief="Source-of-truth for the compiler flags of each translation unit. Typically loaded from compile_commands.json.",
        signature="class CompilationDatabase;",
        example="auto db = clang::tooling::CompilationDatabase::loadFromDirectory(buildDir, err);",
        url=_CLANG + "classclang_1_1tooling_1_1CompilationDatabase.html",
        source="llvm",
    ),
    e(
        "clang-tidy",
        header="clang-tidy",
        since="",
        brief="Linter and static-analysis driver for C and C++. Built on Clang's AST matchers; a check is a registered class with matcher and callback methods.",
        signature="clang-tidy [-checks=<list>] <source> -- <compiler flags>",
        example="clang-tidy -checks=modernize-* main.cpp -- -std=c++20",
        url="https://clang.llvm.org/extra/clang-tidy/",
        source="llvm",
    ),
    e(
        "clang.cindex",
        header="Python: clang.cindex",
        since="",
        brief="Python bindings to libclang. Lets scripts walk a translation unit's cursors without linking against the C++ API.",
        signature="from clang import cindex",
        example="tu = cindex.Index.create().parse(\"main.cpp\")\nfor c in tu.cursor.walk_preorder(): pass",
        url="https://libclang.readthedocs.io/",
        source="llvm",
    ),
    e(
        "llvm::Module",
        header="<llvm/IR/Module.h>",
        since="",
        brief="Container for LLVM IR: global variables, functions, type table, and target metadata for a single compilation unit.",
        signature="class Module;",
        example="llvm::LLVMContext ctx;\nllvm::Module m(\"my\", ctx);",
        url=_LLVM + "classllvm_1_1Module.html",
        source="llvm",
    ),
    e(
        "llvm::IRBuilder",
        header="<llvm/IR/IRBuilder.h>",
        since="",
        brief="Stateful helper for emitting LLVM IR instructions into a basic block at a tracked insertion point.",
        signature="template<class Folder = ConstantFolder, class Inserter = IRBuilderDefaultInserter> class IRBuilder;",
        example="llvm::IRBuilder<> b(bb);\nauto* sum = b.CreateAdd(x, y);",
        url=_LLVM + "classllvm_1_1IRBuilder.html",
        source="llvm",
    ),
    e(
        "llvm::Function",
        header="<llvm/IR/Function.h>",
        since="",
        brief="An LLVM IR function: signature, linkage, attributes, and ordered list of basic blocks.",
        signature="class Function : public GlobalObject;",
        example="auto* fn = llvm::Function::Create(fty, llvm::Function::ExternalLinkage, \"f\", &m);",
        url=_LLVM + "classllvm_1_1Function.html",
        source="llvm",
    ),
    e(
        "llvm::BasicBlock",
        header="<llvm/IR/BasicBlock.h>",
        since="",
        brief="Straight-line sequence of LLVM IR instructions ending with exactly one terminator (branch, return, switch, ...).",
        signature="class BasicBlock;",
        example="auto* bb = llvm::BasicBlock::Create(ctx, \"entry\", fn);",
        url=_LLVM + "classllvm_1_1BasicBlock.html",
        source="llvm",
    ),
]
