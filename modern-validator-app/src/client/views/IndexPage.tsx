
const mapStateToProps = (state: any) => ({
    files: state.documents.list,
});

const mapDispatchToProps = {
    fetchData: () => (dispatch: any) => getDocumentList().then(res => dispatch({ type: DOC_LIST_SUCCESS, payload: res })),
};

export default connect(mapStateToProps, mapDispatchToProps)(IndexPage);

