//dashAgGridComponentFunctions
var dagcomponentfuncs = window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {};

dagcomponentfuncs.Button = function (props) {
    const {setData, data} = props;

    function onClick() {
        setData(data);
    }
    let leftIcon;
    if (props.leftIcon) {
        leftIcon = React.createElement(window.dash_iconify.DashIconify, {
            icon: props.leftIcon,
        });
    }
    return React.createElement(
        'button',
        {
            onClick: onClick,
            variant: props.variant,
            color: props.color,
            leftIcon,
            className: props.className,
        },
        props.value
    );
};

dagcomponentfuncs.ReportLink = function (props) {
    var reportUrl = '/report/' + props.data.id + '/' + props.data.fecha;
    var isActive = props.data.analisis_bioseñales === 'SUCCESS' && props.data.analisis_movimiento === 'SUCCESS';
    // var linkText = isActive ? 'View Report' : props.data.informe;
    var linkStyle = isActive ? {} : { pointerEvents: 'none', color: 'gray' };

    if (isActive === true){
        linkText = 'Generate Report';
        if (props.data.informe === 'SUCCESS'){
            linkText = 'View Report';
        } 
    } else {
        linkText = props.data.informe;
    }

    return React.createElement(
        'a',
        { href: reportUrl, style: linkStyle },
        linkText
    );
};

dagcomponentfuncs.ButtonGroupRenderer = function (props) {
    const {setData, data} = props;  // <-- Igual que en Button

    function onContinue() {
        setData({ action: "continueProcess", patientId: data.id, patientDate: data.fecha });
    }

    function onStop() {
        setData({ action: "stopProcess", patientId: data.id, patientDate: data.fecha });
    }

    function onProcessSelected(event) {
        const selectedProcess = event.target.value;
        if (selectedProcess) {
            setData({ action: "executeProcess", patientId: data.id, patientDate: data.fecha, process: selectedProcess });
        }
    }

    return React.createElement(
        'div',
        {
            className: 'button',
            style: {
                display: 'flex',
                gap: '8px',
                justifyContent: 'left',
                alignItems: 'center',
                height: '100%'
            }
        },
        React.createElement('button', { className: 'btn-continue-process', onClick: onContinue }, 'Continuar'),
        React.createElement('button', { className: 'btn-stop-process', onClick: onStop }, 'Detener'),
        React.createElement(
            'select',
            { className: 'process-dropdown', onChange: onProcessSelected },
            React.createElement('option', { value: '' }, 'Seleccionar proceso'),
            React.createElement('option', { value: 'bin2csv' }, 'Convertir BIN a CSV'),
            React.createElement('option', { value: 'seg_csv' }, 'Segmentar CSV'),
            React.createElement('option', { value: 'bio_analisis' }, 'Análisis de Bioseñales'),
            React.createElement('option', { value: 'analisis_movimiento' }, 'Análisis de Movimiento')
        )
    );
};


dagcomponentfuncs.DeleteButton = function (props) {
    const {setData, data} = props;  // <-- Igual que en Button

    function delete_process() {
        setData({ action: "deletePatient", patientId: data.id });
    }

    return React.createElement(
        'div',
        {
            className: 'button-group',
            style: {
                display: 'flex',
                gap: '8px',
                justifyContent: 'left',
                alignItems: 'center',
                height: '100%'
            }
        },
        React.createElement('button', { className: 'btn-delete-process', onClick: delete_process }, 'Eliminar')
    );
};